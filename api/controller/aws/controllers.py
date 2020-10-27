import json
import time
import uuid

import botocore
import pinject
from jsonschema import validate as validate_schema
from tornado import gen

from assistants.deployments.aws.aws_deployment import AwsDeployment
from assistants.deployments.aws.lambda_function import LambdaWorkflowState
from assistants.deployments.aws.utils import get_base_lambda_code
from assistants.deployments.diagram.workflow_states import StateTypes
from assistants.deployments.teardown import teardown_infrastructure
from controller import BaseHandler
from controller.aws.schemas import *
from controller.decorators import authenticated, disable_on_overdue_payment
from controller.logs.actions import delete_logs
from controller.projects.actions import update_project_config
from models import InlineExecutionLambda, Project, Deployment, DeploymentLog
from pyexceptions.builds import BuildException
from utils.general import get_random_node_id, attempt_json_decode
from utils.locker import AcquireFailure


class RunTmpLambdaDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, builder_manager):
        pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class RunTmpLambda(BaseHandler):
    dependencies = RunTmpLambdaDependencies
    builder_manager = None

    @authenticated
    @disable_on_overdue_payment
    @gen.coroutine
    def post(self):
        """
        Build, deploy, and run an AWS lambda function.

        Always upon completion the Lambda should be deleted!
        """
        validate_schema(self.json, RUN_TMP_LAMBDA_SCHEMA)

        self.logger("Building Lambda package...")

        credentials = self.get_authenticated_user_cloud_configuration()

        random_node_id = get_random_node_id()

        # Try to parse Lambda input as JSON
        self.json["input_data"] = attempt_json_decode(
            self.json["input_data"]
        )

        backpack_data = {}

        if "backpack" in self.json:
            backpack_data = attempt_json_decode(
                self.json["backpack"]
            )

        # Dummy pipeline execution ID
        pipeline_execution_id = "SHOULD_NEVER_HAPPEN_TMP_LAMBDA_RUN"

        # This needs:
        # project_id
        # project_name
        # project_config
        # task_spawner
        # credentials
        deployment_diagram = AwsDeployment(
            pipeline_execution_id,
            None,
            project_config={
                "logging": {
                    "level": "LOG_NONE"
                }
            },
            credentials=credentials,
            task_spawner=self.task_spawner
        )

        inline_lambda = LambdaWorkflowState(
            credentials,
            str(uuid.uuid4()),
            random_node_id,
            StateTypes.LAMBDA,
            is_inline_execution=True
        )
        inline_lambda.setup(deployment_diagram, self.json)

        inline_lambda_hash_key = inline_lambda.get_content_hash()

        # Check if we already have an inline execution Lambda for it.
        cached_inline_execution_lambda = self.dbsession.query(InlineExecutionLambda).filter_by(
            aws_account_id=credentials["id"],
            unique_hash_key=inline_lambda_hash_key
        ).first()

        # We can skip this if we already have a cached execution
        if cached_inline_execution_lambda:
            self.logger("Inline execution is already cached as a Lambda, doing a hotload...")

            # Update the latest execution time to be the current timestamp
            # This informs our garbage collection to ensure we always delete the Lambda
            # that was run the longest ago (so that people encounter cache-misses as
            # little as possible.)
            cached_inline_execution_lambda.last_used_timestamp = int(time.time())

            # Update it in the database
            self.dbsession.commit()

            cached_inline_execution_lambda_dict = cached_inline_execution_lambda.to_dict()
        else:
            # noinspection PyUnresolvedReferences
            try:
                yield inline_lambda.predeploy(self.task_spawner)
                yield inline_lambda.deploy(
                    self.task_spawner, project_id=None, project_config=None
                )
            except BuildException as build_exception:
                self.write({
                    "success": False,
                    "msg": "An error occurred while building the Code Block package.",
                    "log_output": build_exception.build_output
                })
                raise gen.Return()
            except botocore.exceptions.ClientError as boto_error:
                self.logger("An exception occurred while setting up the Code Block.")
                self.logger(boto_error)

                error_message = boto_error.response["Error"]["Message"] + " (Code: " + boto_error.response["Error"]["Code"] + ")"

                self.write({
                    "success": False,
                    "msg": error_message,
                    "log_output": ""
                })
                raise gen.Return()

        execute_lambda_params = {
            "_refinery": {
                "backpack": backpack_data,
                "throw_exceptions_fully": True,
                "input_data": self.json["input_data"],
                "temporary_execution": True
            }
        }

        # Get inline execution code
        inline_execution_code = get_base_lambda_code(
            self.app_config,
            self.json["language"],
            self.json["code"]
        )

        if self.json["language"] == "go1.12":
            inline_lambda.code = inline_execution_code

            try:
                binary_s3_path = yield self.builder_manager.get_go112_binary_s3(
                    credentials,
                    inline_lambda
                )
            except BuildException as build_exception:
                self.write({
                    "success": False,
                    "msg": "An error occurred while building the Code Block package.",
                    "log_output": build_exception.build_output
                })
                raise gen.Return()

            execute_lambda_params["_refinery"]["inline_code"] = {
                "s3_path": binary_s3_path,
                "shared_files": self.json["shared_files"]
            }
        else:
            # Generate Lambda run input
            execute_lambda_params["_refinery"]["inline_code"] = {
                "base_code": inline_execution_code,
                "shared_files": self.json["shared_files"]
            }

        if "debug_id" in self.json:
            execute_lambda_params["_refinery"]["live_debug"] = {
                "debug_id": self.json["debug_id"],
                "websocket_uri": self.app_config.get("LAMBDA_CALLBACK_ENDPOINT"),
            }

        self.logger(f"Executing Lambda '{inline_lambda.arn}'...")

        lambda_result = yield self.task_spawner.execute_aws_lambda(
            credentials,
            inline_lambda.arn,
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

        try:
            return_data = json.loads(
                lambda_result["returned_data"]
            )
            s3_object = yield self.task_spawner.read_from_s3(
                credentials,
                credentials["logs_bucket"],
                return_data["_refinery"]["indirect"]["s3_path"]
            )
            s3_dict = json.loads(
                s3_object
            )
            lambda_result["returned_data"] = json.dumps(
                s3_dict["return_data"],
                indent=4,
            )
            lambda_result["logs"] = s3_dict["program_output"]
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

        # If it's not a supported language for inline execution that
        # means that it needs to be manually deleted since it's not in the
        # regular garbage collection pool.
        """
		if self.json[ "language" ] in NOT_SUPPORTED_INLINE_EXECUTION_LANGUAGES:
			self.logger( "Deleting Lambda..." )

			# Now we delete the lambda, don't yield because we don't need to wait
			delete_result = self.task_spawner.delete_aws_lambda(
				credentials,
				random_node_id
			)
		"""

        self.write({
            "success": True,
            "result": lambda_result
        })


class InfraTearDownDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(
        self,
        api_gateway_manager,
        lambda_manager,
        schedule_trigger_manager,
        sns_manager,
        sqs_manager
    ):
        pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class InfraTearDown(BaseHandler):
    dependencies = InfraTearDownDependencies
    api_gateway_manager = None
    lambda_manager = None
    schedule_trigger_manager = None
    sns_manager = None
    sqs_manager = None

    @authenticated
    @gen.coroutine
    def post(self):

        teardown_nodes = self.json["teardown_nodes"]

        credentials = self.get_authenticated_user_cloud_configuration()

        teardown_operation_results = yield teardown_infrastructure(
            self.api_gateway_manager,
            self.lambda_manager,
            self.schedule_trigger_manager,
            self.sns_manager,
            self.sqs_manager,
            credentials,
            teardown_nodes
        )

        # Delete our logs
        # No need to yield till it completes
        delete_logs(
            self.task_spawner,
            credentials,
            self.json["project_id"]
        )

        self.write({
            "success": True,
            "result": teardown_operation_results
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
    def __init__(self, lambda_manager, api_gateway_manager, schedule_trigger_manager, sns_manager, sqs_manager):
        pass


def filter_teardown_nodes(teardown_nodes):
    return [
        node for node in teardown_nodes
        if node["type"] not in ["lambda", "api_endpoint", "api_gateway", "sqs_queue", "sns_topic"]
    ]


class DeployDiagram(BaseHandler):
    dependencies = DeployDiagramDependencies
    lambda_manager = None
    api_gateway_manager = None
    schedule_trigger_manager = None
    sns_manager = None
    sqs_manager = None

    @gen.coroutine
    def cleanup_deployment(self, deployment_diagram, credentials, successful_deploy):
        yield deployment_diagram.remove_workflow_states(
            self.api_gateway_manager,
            self.lambda_manager,
            self.schedule_trigger_manager,
            self.sns_manager,
            self.sqs_manager,
            credentials,
            successful_deploy
        )

        # Delete our logs
        # No need to yield till it completes
        delete_logs(
            self.task_spawner,
            credentials,
            deployment_diagram.project_id
        )

    @authenticated
    @disable_on_overdue_payment
    @gen.coroutine
    def do_diagram_deployment(self, project_name, project_id, diagram_data, project_config, force_redeploy):
        credentials = self.get_authenticated_user_cloud_configuration()

        org_id = self.get_authenticated_user_org().id

        latest_deployment = self.dbsession.query(Deployment).filter_by(
            project_id=project_id
        ).order_by(
            Deployment.timestamp.desc()
        ).first()

        latest_deployment_json = None
        if not force_redeploy and latest_deployment is not None:
            latest_deployment_json = json.loads(latest_deployment.deployment_json)

        # Kill the current session because deployment can take a very long time.
        # A new session will be automatically opened when the session is grabbed again.
        self.dbsession.close()

        self._dbsession = None

        # Model a deployment in memory to handle the deployment of each state
        deployment_diagram: AwsDeployment = AwsDeployment(
            project_id,
            project_name,
            project_config,
            self.task_spawner,
            credentials,
            api_gateway_manager=self.api_gateway_manager,
            latest_deployment=latest_deployment_json
        )

        exceptions = yield deployment_diagram.deploy_diagram(diagram_data)

        # Check if the deployment failed
        if len(exceptions) != 0:
            self.logger("We are now rolling back the deployments we've made...", "error")

            yield self.cleanup_deployment(deployment_diagram, credentials, successful_deploy=False)

            self.logger("We've completed our rollback, returning an error...", "error")

            # For now we'll just raise
            self.write({
                "success": True,  # Success meaning we caught it
                "result": {
                    "deployment_success": False,
                    "exceptions": [e.serialize() for e in exceptions],
                }
            })
            raise gen.Return()

        # Cleanup any unused resources
        yield self.cleanup_deployment(deployment_diagram, credentials, successful_deploy=True)

        # TODO: Update the project data? Deployments should probably be an explicit "Save Project" action.

        # Add a reference to this deployment from the associated project
        existing_project = self.dbsession.query(Project).filter_by(
            id=project_id
        ).first()

        if existing_project is None:
            self.write({
                "success": False,
                "code": "DEPLOYMENT_UPDATE",
                "msg": "Unable to find project when updating deployment information.",
            })

            # TODO we probably want to teardown the deployment if this is the case

            raise gen.Return()

        serialized_deployment = deployment_diagram.serialize()

        new_deployment = Deployment()
        new_deployment.organization_id = org_id
        new_deployment.project_id = project_id
        new_deployment.deployment_json = json.dumps(
           serialized_deployment
        )

        existing_project.deployments.append(
            new_deployment
        )

        deployment_log = DeploymentLog()
        deployment_log.org_id = org_id

        self.dbsession.add(deployment_log)
        self.dbsession.commit()

        # Update project config
        self.logger("Updating database with new project config...")
        update_project_config(
            self.dbsession,
            project_id,
            deployment_diagram.get_updated_config()
        )

        self.write({
            "success": True,
            "result": {
                "deployment_success": True,
                "diagram_data": serialized_deployment,
                "project_id": project_id,
                "deployment_id": new_deployment.id,
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

        project_name = self.json["project_name"]
        project_id = self.json["project_id"]
        diagram_data = json.loads(self.json["diagram_data"])
        project_config = self.json["project_config"]
        force_redeploy = self.json["force_redeploy"]

        lock_id = "deploy_diagram_" + project_id

        task_lock = self.task_locker.lock(self.dbsession, lock_id)

        try:
            # Enforce that we are only attempting to do this multiple times simultaneously for the same project
            with task_lock:
                yield self.do_diagram_deployment(
                    project_name, project_id, diagram_data, project_config, force_redeploy)

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
