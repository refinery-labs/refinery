import json
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
from data_types.deployment_stages import DeploymentStages, DeploymentStates
from assistants.deployments.serverless.builder import ServerlessBuilder
from assistants.deployments.serverless.dismantler import ServerlessDismantler, ServerlessDismantlerFactory
from assistants.deployments.serverless.exceptions import RefineryDeploymentException
from assistants.deployments.serverless.module_builder import ServerlessModuleBuilder
from models import Deployment, Project, DeploymentLog
from models.initiate_database import session_scope
from services.workflow_manager.workflow_manager_service import WorkflowManagerException
from tasks.athena import create_project_id_log_table
from utils.locker import AcquireFailure, LockFactory


class DeployStageConfig:
    credentials = None
    org_id = None
    project_id = None
    stage: DeploymentStages = None
    diagram_data = None
    deploy_workflows = True
    create_log_table = True
    new_deployment_id = None

    @pinject.copy_args_to_public_fields
    def __init__(
            self,
            credentials,
            org_id,
            project_id,
            stage: DeploymentStages,
            diagram_data,
            deploy_workflows=True,
            create_log_table=True,
    ):
        self.new_deployment_id = str(uuid4())


class DeploymentManager(object):
    task_spawner: TaskSpawner = None
    app_config: AppConfig = None
    aws_client_factory: AwsClientFactory = None
    db_session_maker = None
    logger = None
    workflow_manager_service = None
    serverless_module_builder: ServerlessModuleBuilder = None
    serverless_dismantler_factory: ServerlessDismantlerFactory = None
    lock_factory: LockFactory = None

    # noinspection PyUnresolvedReferences
    @pinject.copy_args_to_public_fields
    def __init__(
        self,
        logger,
        task_spawner,
        app_config,
        db_session_maker,
        aws_client_factory,
        workflow_manager_service,
        serverless_module_builder,
        serverless_dismantler_factory,
        lock_factory,
        loop=None
    ):
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
    def get_deployment_with_id(dbsession, deployment_id) -> Deployment:
        return dbsession.query(Deployment).filter_by(
            deployment_id=deployment_id
        ).first()

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

    def mark_deployment_started(self, deployment_id):
        with session_scope(self.db_session_maker) as dbsession:
            dbsession.query(Deployment).filter_by(
                deployment_id=deployment_id
            ).update(
                dict(state=DeploymentStates.in_progress)
            )

    def mark_deployment_failed(self, deployment_id, error):
        with session_scope(self.db_session_maker) as dbsession:
            dbsession.query(Deployment).filter_by(
                deployment_id=deployment_id
            ).update(
                dict(state=DeploymentStates.failed, log=error)
            )

    @staticmethod
    def query_project_deployments(dbsession, project_id, stage=None, deployment_tag=None) -> Deployment:
        query_filters = {
            "project_id": project_id
        }
        if stage is not None:
            query_filters["stage"] = stage
        if deployment_tag is not None:
            query_filters["deployment_tag"] = deployment_tag

        return dbsession.query(Deployment).filter_by(
            **query_filters
        ).order_by(
            Deployment.timestamp.desc()
        ).all()

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

    def start_deploy_stage(
        self,
        config: DeployStageConfig
    ):
        with session_scope(self.db_session_maker) as dbsession:
            new_deployment = Deployment(id=config.new_deployment_id)
            new_deployment.organization_id = config.org_id
            new_deployment.project_id = config.project_id
            new_deployment.stage = config.stage.value
            dbsession.add(new_deployment)

        # Do not await this async function
        self.deploy_stage(config)

        return config.new_deployment_id

    @run_on_executor
    def deploy_stage(self, config: DeployStageConfig):
        lock_id = f"deploy_diagram_{config.project_id}"

        try:
            # Enforce that we are only attempting to do this multiple times simultaneously for the same project
            with self.lock_factory.lock(lock_id):
                self.deploy_stage(config)

        except AcquireFailure:
            error = f"Unable to acquire deploy diagram lock for {config.project_id}"
            self.mark_deployment_failed(config.new_deployment_id, error)
            self.logger(error)
            raise RefineryDeploymentException(error)
        except Exception as e:
            error = "an error occurred while trying to deploy the project."
            self.mark_deployment_failed(config.new_deployment_id, error)
            raise RefineryDeploymentException(error)

    def do_deploy_stage(
        self,
        config: DeployStageConfig
    ):
        # TODO check for collisions
        if config.new_deployment_id is None:
            error = "new deployment ID is not set"
            self.mark_deployment_failed(config.new_deployment_id, error)
            raise RefineryDeploymentException(error)

        with session_scope(self.db_session_maker) as dbsession:
            latest_deployment = self.get_latest_deployment(dbsession, config.project_id, config.stage)

            previous_deployment_json = {}
            if latest_deployment:
                previous_deployment_json = json.loads(latest_deployment.deployment_json)

        previous_build_id = previous_deployment_json.get('build_id') if previous_deployment_json else None

        builder = ServerlessBuilder(
            self.app_config,
            self.aws_client_factory,
            self.serverless_module_builder,
            config.credentials,
            config.project_id,
            config.new_deployment_id,
            previous_build_id,
            config.stage.value,
            config.diagram_data
        )

        self.mark_deployment_started(config.new_deployment_id)

        self.logger(f"Deploying project: {config.project_id} with deployment id: {config.new_deployment_id}")
        deployment_config = builder.build(rebuild=True)

        if deployment_config is None:
            error = "an error occurred while trying to build and deploy the project."
            self.mark_deployment_failed(config.new_deployment_id, error)
            raise RefineryDeploymentException(error)

        if config.deploy_workflows:
            try:
                self.workflow_manager_service.create_workflows_for_deployment(deployment_config)
            except WorkflowManagerException as e:
                error = "an error occurred while trying to create workflows in the workflow manager."
                self.mark_deployment_failed(config.new_deployment_id, error)
                self.logger("An error occurred while trying to create workflows in the Workflow Manager: " + str(e), "error")
                raise RefineryDeploymentException(error)

        with session_scope(self.db_session_maker) as dbsession:
            new_deployment = self.get_deployment_with_id(dbsession, config.new_deployment_id)
            new_deployment.deployment_json = json.dumps(deployment_config)
            new_deployment.tag = builder.deployment_tag
            new_deployment.state = DeploymentStates.succeeded

            existing_project = self.get_existing_project(dbsession, config.project_id)
            existing_project.deployments.append(new_deployment)

            deployment_log = DeploymentLog()
            deployment_log.org_id = config.org_id

        if config.create_log_table:
            project_log_table_future = self.create_project_id_log_table(
                config.credentials,
                config.project_id
            )

    @gen.coroutine
    def remove_project_deployments(self, credentials, project_id, remove_workflows=True):
        with session_scope(self.db_session_maker) as dbsession:
            project_deployments = self.query_project_deployments(dbsession, project_id)

            if project_deployments is None:
                raise gen.Return()

        for project_deployment in project_deployments:
            deployment_json = json.loads(project_deployment.deployment_json)

            yield self.remove_stage(credentials, project_id, project_deployment.id, deployment_json, project_deployment.stage, remove_workflows)

    @gen.coroutine
    def remove_latest_stage(self, credentials, project_id, stage, remove_workflows=True):
        with session_scope(self.db_session_maker) as dbsession:
            latest_deployment = self.get_latest_deployment(dbsession, project_id, stage)

            if latest_deployment is None:
                raise gen.Return()

            deployment_id = latest_deployment.id

        yield self.remove_stage(credentials, project_id, deployment_id, stage, remove_workflows)

    @run_on_executor
    def remove_stage(
        self,
        credentials,
        project_id,
        deployment_id,
        deployment_json,
        stage: DeploymentStages,
        remove_workflows=True,
        remove_logs=True
    ):
        build_id = deployment_json.get('build_id') if deployment_json else None

        serverless_dismantler = self.serverless_dismantler_factory.new_serverless_dismantler(
            credentials,
            build_id,
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
