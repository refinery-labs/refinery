import json

import pinject
from jsonschema import validate as validate_schema
from tornado import gen

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory
from controller import BaseHandler
from controller.aws.schemas import *
from controller.decorators import authenticated, disable_on_overdue_payment
from controller.logs.actions import delete_logs
from controller.projects.actions import update_project_config
from data_types.deployment_stages import DeploymentStages

from deployment.deployment_manager import DeploymentManager
from deployment.serverless.exceptions import RefineryDeploymentException
from models import DeploymentLog
from tasks.athena import create_project_id_log_table
from utils.general import attempt_json_decode
from utils.locker import AcquireFailure


class RunTmpLambdaDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, builder_manager, aws_client_factory, deployment_manager):
        pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class RunTmpLambda(BaseHandler):
    dependencies = RunTmpLambdaDependencies
    builder_manager = None
    aws_client_factory = None
    deployment_manager: DeploymentManager = None

    @gen.coroutine
    def get_lambda_arn(self, credentials, org_id, project_id, diagram_data, workflow_state_id):
        stage = DeploymentStages.dev

        # lambda_info = yield self.deployment_manager.find_existing_lambda(credentials, project_id, stage, workflow_state_id)
        # if lambda_info is not None:
        #     raise gen.Return(lambda_info)

        try:
            deployed_project = yield self.deployment_manager.deploy_stage(
                credentials, org_id, project_id, stage, diagram_data, deploy_workflows=False, create_log_table=False
            )
        except RefineryDeploymentException as e:
            self.logger(str(e))
            raise gen.Return(None)

        deployment_config = deployed_project["deployment_config"]

        workflow_states = deployment_config["workflow_states"]
        workflow_state_lookup = {ws["id"]: ws for ws in workflow_states}
        function_workflow_state = workflow_state_lookup.get(workflow_state_id)
        if function_workflow_state is None:
            self.logger(f"cannot find function with id: {workflow_state_id}")
            raise gen.Return(None)

        arn, _, version = function_workflow_state["arn"].rpartition(":")
        raise gen.Return((arn, version))

    @authenticated
    @disable_on_overdue_payment
    @gen.coroutine
    def post(self):
        """
        Build, deploy, and run an AWS lambda function.

        Always upon completion the Lambda should be deleted!
        """
        validate_schema(self.json, RUN_TMP_LAMBDA_SCHEMA)

        project_id = self.json["project_id"]
        diagram_data = json.loads(self.json["diagram_data"])
        block_id = self.json["block_id"]

        self.logger("Building Lambda package...")

        credentials = self.get_authenticated_user_cloud_configuration()
        org_id = self.get_authenticated_user_org().id

        # Try to parse Lambda input as JSON
        self.json["input_data"] = attempt_json_decode(
            self.json["input_data"]
        )

        backpack_data = {}

        if "backpack" in self.json:
            backpack_data = attempt_json_decode(
                self.json["backpack"]
            )

        execute_lambda_params = {
            "backpack": backpack_data,
            "block_input": self.json["input_data"],
        }

        if "debug_id" in self.json:
            # TODO implement live debugging
            """
            execute_lambda_params["_refinery"]["live_debug"] = {
                "debug_id": self.json["debug_id"],
                "websocket_uri": self.app_config.get("LAMBDA_CALLBACK_ENDPOINT"),
            }
            """
            pass


        # TODO this code is needed if going from package to docker uri
        # need to figure out how to get around this maybe?
        """
        yield self.deployment_manager.remove_latest_stage(
            credentials, project_id, DeploymentStages.dev, remove_workflows=False
        )
        """

        lambda_info = yield self.get_lambda_arn(credentials, org_id, project_id, diagram_data, block_id)
        if lambda_info is None:
            self.logger(f"Unable to get arn for lambda: {block_id} for project: {project_id}")
            self.write({
                "success": False,
                "msg": "Unable to build and deploy lambda.",
                "log_output": ""
            })
            raise gen.Return()

        lambda_arn, version = lambda_info

        self.logger(f"Executing Lambda '{lambda_arn}'...")

        lambda_result = yield self.task_spawner.execute_aws_lambda_with_version(
            credentials,
            lambda_arn,
            version,
            execute_lambda_params
        )

        if "Task timed out after " in lambda_result["logs"]:
            self.logger("Lambda timed out while being executed!")
            self.write({
                "success": False,
                "msg": "The Code Block timed out while running, you may have an infinite loop or you may need to increase your Code Block's Max Execution Time.",
                "log_output": ""
            })
            raise gen.Return()

        lambda_execution_result = {}
        try:
            return_data = json.loads(
                lambda_result["returned_data"]
            )
            lambda_execution_result["returned_data"] = return_data["result"] if "result" in return_data else ""
            lambda_execution_result["logs"] = lambda_result["logs"] if "logs" in lambda_result else ""
        except Exception as e:
            self.logger("Exception occurred while loading temporary Lambda return data: ")
            self.logger(e)
            self.logger("Raw Lambda return data: ")
            self.logger(lambda_result)

            # Clearer logging for raw Lambda error output
            if "logs" in lambda_result:
                print((lambda_result["logs"]))

            self.write({
                "success": False,
                "msg": "An exception occurred while running the Lambda.",
                "log_output": str(e)
            })
            raise gen.Return()

        self.write({
            "success": True,
            "result": lambda_execution_result
        })


class InfraTearDownDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(
        self,
        deployment_manager
    ):
        pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class InfraTearDown(BaseHandler):
    dependencies = InfraTearDownDependencies
    deployment_manager: DeploymentManager = None

    @authenticated
    @gen.coroutine
    def post(self):
        credentials = self.get_authenticated_user_cloud_configuration()

        project_id = self.json["project_id"]
        deployment_id = self.json["deployment_id"]

        yield self.deployment_manager.remove_stage(
            credentials, project_id, deployment_id, DeploymentStages.prod
        )

        self.write({
            "success": True,
            "result": "done"
        })


class InfraCollisionCheck(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        # TODO remove this endpoint
        self.write({
            "success": True
        })


class DeployDiagramDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, deployment_manager, aws_client_factory):
        pass


class DeployDiagram(BaseHandler):
    dependencies = DeployDiagramDependencies
    deployment_manager: DeploymentManager = None
    aws_client_factory: AwsClientFactory = None

    @gen.coroutine
    def create_project_id_log_table(self, credentials, project_id):
        return create_project_id_log_table(
            self.aws_client_factory,
            credentials,
            project_id
        )

    @gen.coroutine
    def do_diagram_deployment(self, project_id, diagram_data, project_config):
        credentials = self.get_authenticated_user_cloud_configuration()
        org_id = self.get_authenticated_user_org().id
        stage = DeploymentStages.prod

        try:
            deployed_project = yield self.deployment_manager.deploy_stage(
                credentials, org_id, project_id, stage, diagram_data
            )
        except RefineryDeploymentException as e:
            self.write({
                "success": False,
                "code": "DEPLOYMENT",
                "msg": str(e)
            })
            raise gen.Return()

        self.logger("Updating database with new project config...")
        update_project_config(
            self.dbsession,
            project_id,
            project_config
        )

        deployment_id = deployed_project["deployment_id"]
        deployment_config = deployed_project["deployment_config"]

        self.write({
            "success": True,
            "result": {
                "deployment_success": True,
                "project_id": project_id,
                "deployment_id": deployment_id,
                "diagram_data": deployment_config,
            }
        })

    @authenticated
    @disable_on_overdue_payment
    @gen.coroutine
    def post(self):
        # TODO: Add jsonschema
        self.logger("Deploying diagram to production...")

        # Ensure user is owner of the project
        if not self.is_owner_of_project(self.json["project_id"]):
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have privileges to deploy that!",
            })
            raise gen.Return()

        project_id = self.json["project_id"]
        diagram_data = json.loads(self.json["diagram_data"])
        project_config = self.json["project_config"]

        lock_id = "deploy_diagram_" + project_id

        task_lock = self.task_locker.lock(self.dbsession, lock_id)

        try:
            # Enforce that we are only attempting to do this multiple times simultaneously for the same project
            with task_lock:
                yield self.do_diagram_deployment(
                    project_id,diagram_data, project_config)

        except AcquireFailure:
            self.logger("Unable to acquire deploy diagram lock for " + project_id)
            self.write({
                "success": False,
                "code": "DEPLOYMENT_LOCK_FAILURE",
                "msg": "Deployment for this project is already in progress",
            })


class GetAWSConsoleCredentials(BaseHandler):
    @authenticated
    @disable_on_overdue_payment
    @gen.coroutine
    def get(self):
        """
        Pull the AWS credentials for the customer to log into the console.
        This is important early on so that they can still get all the serverless
        advantages that we haven't abstracted upon (and to use Cloudwatch, etc).
        """
        credentials = self.get_authenticated_user_cloud_configuration()

        aws_console_signin_url = "https://{account_id}.signin.aws.amazon.com/console/?region={region_name}".format(
            account_id=credentials["account_id"],
            region_name=self.app_config.get("region_name")
        )

        self.write({
            "success": True,
            "console_credentials": {
                "username": credentials["iam_admin_username"],
                "password": credentials["iam_admin_password"],
                "signin_url": aws_console_signin_url,
            }
        })
