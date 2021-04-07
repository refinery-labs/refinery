import json
from functools import cached_property
from uuid import uuid4

import pinject
import tornado
from botocore.exceptions import ClientError
from tornado import gen
from tornado.concurrent import futures, run_on_executor
from tornado.ioloop import IOLoop

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory
from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from config.app_config import AppConfig
from controller.logs.actions import delete_logs
from data_types.deployment_stages import DeploymentStages
from deployment.serverless.builder import ServerlessBuilder
from deployment.serverless.dismantler import ServerlessDismantler
from deployment.serverless.exceptions import RefineryDeploymentException
from deployment.serverless.module_builder import ServerlessModuleBuilder
from models import Deployment, Project, DeploymentLog
from models.initiate_database import session_scope
from services.workflow_manager.workflow_manager_service import WorkflowManagerException
from tasks.athena import create_project_id_log_table


class DeploymentManager(object):
    task_spawner: TaskSpawner = None
    app_config: AppConfig = None
    aws_client_factory: AwsClientFactory = None
    db_session_maker = None
    logger = None
    workflow_manager_service = None
    serverless_module_builder: ServerlessModuleBuilder = None

    # noinspection PyUnresolvedReferences
    @pinject.copy_args_to_public_fields
    def __init__(self, logger, task_spawner, app_config, db_session_maker, aws_client_factory, workflow_manager_service, serverless_module_builder, loop=None):
        self.executor = futures.ThreadPoolExecutor(10)
        self.loop = loop or tornado.ioloop.IOLoop.current()

    def lambda_function(self, credentials):
        return self.aws_client_factory.get_aws_client(
            "lambda",
            credentials
        )

    @staticmethod
    def get_existing_project(dbsession, project_id):
        # Add a reference to this deployment from the associated project
        existing_project = dbsession.query(Project).filter_by(
            id=project_id
        ).first()

        if existing_project is None:
            raise RefineryDeploymentException("Unable to find project when updating deployment information.")

        return existing_project

    @staticmethod
    def get_deployment_with_tag(dbsession, tag) -> Deployment:
        return dbsession.query(Deployment).filter_by(
            tag=tag
        ).order_by(
            Deployment.timestamp.desc()
        ).first()

    @staticmethod
    def get_latest_deployment(dbsession, project_id, stage) -> Deployment:
        return dbsession.query(Deployment).filter_by(
            project_id=project_id, stage=stage
        ).order_by(
            Deployment.timestamp.desc()
        ).first()

    @run_on_executor
    def find_existing_lambda(self, credentials, project_id, stage: DeploymentStages, workflow_state_id):
        with session_scope(self.db_session_maker) as dbsession:
            latest_deployment = self.get_latest_deployment(dbsession, project_id, stage)
            if latest_deployment is None:
                return None

            deployment = json.loads(latest_deployment.deployment_json)

        workflow_states = deployment["workflow_states"]
        workflow_state = next(filter(lambda ws: ws["id"] == workflow_state_id, workflow_states))
        if workflow_state is None:
            return None

        lambda_arn, _, version = workflow_state["arn"].rpartition(":")
        lambda_client = self.lambda_function(credentials)
        try:
            lambda_client.get_function(
                FunctionName=lambda_arn,
                Qualifier=version
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise
            return None
        return lambda_arn, version

    @gen.coroutine
    def create_project_id_log_table(self, credentials, project_id):
        return create_project_id_log_table(
            self.aws_client_factory,
            credentials,
            project_id
        )

    @run_on_executor
    def deploy_stage(
            self,
            credentials,
            org_id,
            project_id,
            stage: DeploymentStages,
            diagram_data,
            deploy_workflows=True,
            create_log_table=True,
            function_name=None,
            new_deployment_id=None
    ):

        with session_scope(self.db_session_maker) as dbsession:
            latest_deployment = self.get_latest_deployment(dbsession, project_id, stage)

            previous_deployment_json = {}
            if latest_deployment:
                previous_deployment_json = json.loads(latest_deployment.deployment_json)

        previous_build_id = previous_deployment_json.get('build_id') if previous_deployment_json else None

        # TODO check for collisions
        if new_deployment_id is None:
            new_deployment_id = str(uuid4())

        builder = ServerlessBuilder(
            self.app_config,
            self.aws_client_factory,
            self.serverless_module_builder,
            credentials,
            project_id,
            new_deployment_id,
            previous_build_id,
            stage.value,
            diagram_data
        )

        self.logger(f"Deploying project: {project_id} with deployment id: {new_deployment_id}")
        deployment_config = builder.build(rebuild=True, function_name=function_name)

        if deployment_config is None:
            raise RefineryDeploymentException("an error occurred while trying to build and deploy the project.",)

        if deploy_workflows:
            try:
                self.workflow_manager_service.create_workflows_for_deployment(deployment_config)
            except WorkflowManagerException as e:
                self.logger("An error occurred while trying to create workflows in the Workflow Manager: " + str(e), "error")
                raise RefineryDeploymentException("an error occurred while trying to create workflows in the workflow manager.")

        # Create deployment metadata
        new_deployment = Deployment(id=new_deployment_id)
        new_deployment.organization_id = org_id
        new_deployment.project_id = project_id
        new_deployment.deployment_json = json.dumps(deployment_config)
        new_deployment.stage = stage.value
        new_deployment.tag = builder.deployment_tag

        with session_scope(self.db_session_maker) as dbsession:
            existing_project = self.get_existing_project(dbsession, project_id)
            existing_project.deployments.append(new_deployment)
            deployment_id = new_deployment.id

            deployment_log = DeploymentLog()
            deployment_log.org_id = org_id

        if create_log_table:
            project_log_table_future = self.create_project_id_log_table(
                credentials,
                project_id
            )

        return {
            "deployment_id": deployment_id,
            "deployment_config": deployment_config
        }

    @gen.coroutine
    def remove_latest_stage(self, credentials, project_id, stage, remove_workflows=True):
        with session_scope(self.db_session_maker) as dbsession:
            latest_deployment = self.get_latest_deployment(dbsession, project_id, stage)

            if latest_deployment is None:
                raise gen.Return()

            deployment_id = latest_deployment.id

        yield self.remove_stage(credentials, project_id, deployment_id, stage, remove_workflows)

    @run_on_executor
    def remove_stage(self, credentials, project_id, deployment_id, stage: DeploymentStages, remove_workflows=True, remove_logs=True):
        with session_scope(self.db_session_maker) as dbsession:
            latest_deployment = self.get_latest_deployment(dbsession, project_id, stage)

            previous_deployment_json = {}
            if latest_deployment:
                previous_deployment_json = json.loads(latest_deployment.deployment_json)

            build_id = previous_deployment_json.get('build_id') if previous_deployment_json else None

        if build_id is None:
            raise RefineryDeploymentException("unable to find built application; build ID was not given")

        serverless_dismantler = ServerlessDismantler(
            self.app_config,
            self.aws_client_factory,
            credentials,
            build_id,
            deployment_id,
            stage.value
        )

        # TODO check return?
        # What happens on failure?
        serverless_dismantler.dismantle()

        if remove_workflows:
            self.workflow_manager_service.delete_deployment_workflows(deployment_id)

        if remove_logs:
            # Delete our logs
            # No need to yield till it completes
            delete_logs(
                self.task_spawner,
                credentials,
                project_id
            )
