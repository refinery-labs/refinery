import json
import time
import uuid

import botocore
import pinject
from jsonschema import validate as validate_schema
from tornado import gen

from assistants.deployments.aws_workflow_manager.aws_deployment import AwsDeployment
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
from services.workflow_manager.workflow_manager_service import WorkflowManagerService, WorkflowManagerException
from utils.general import get_random_node_id, attempt_json_decode
from utils.locker import AcquireFailure


class RunTmpLambdaDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, builder_manager, aws_client_factory):
        pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class RunTmpLambda(BaseHandler):
    dependencies = RunTmpLambdaDependencies
    builder_manager = None
    aws_client_factory = None

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

        deployment_diagram = AwsDeployment(
            pipeline_execution_id,
            None,
            project_config={
                "logging": {
                    "level": "LOG_NONE"
                }
            },
            app_config=self.app_config,
            credentials=credentials,
            aws_client_factory=self.aws_client_factory,
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
            "backpack": backpack_data,
            "block_input": self.json["input_data"],
        }

        # Get inline execution code
        inline_execution_code = get_base_lambda_code(
            self.app_config,
            self.json["language"],
            self.json["code"]
        )

        if self.json["language"] == "go1.12":
            self.write({
                "success": False,
                "msg": "Language currently not supported for code runner",
                "log_output": ""
            })

        if "debug_id" in self.json:
            # TODO implement live debugging
            """
            execute_lambda_params["_refinery"]["live_debug"] = {
                "debug_id": self.json["debug_id"],
                "websocket_uri": self.app_config.get("LAMBDA_CALLBACK_ENDPOINT"),
            }
            """
            pass

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
            "result": lambda_execution_result
        })


class InfraTearDownDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(
        self,
        api_gateway_manager,
        lambda_manager,
        schedule_trigger_manager,
        sns_manager,
        sqs_manager,
        workflow_manager_service
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
    workflow_manager_service: WorkflowManagerService = None

    @authenticated
    @gen.coroutine
    def post(self):
        version_token = self.json["version_token"]

        if version_token != "5e92c868":
            self.write({
                "success": False,
                "error": "Attempted tear down with old client-side code. Please refresh your bundle and include the "
                         "proper 'version_token'."
            })
            raise gen.Return()

        teardown_nodes = self.json["teardown_nodes"]

        credentials = self.get_authenticated_user_cloud_configuration()

        yield self._append_transition_arns(self.json['deployment_id'], teardown_nodes)
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

        self.workflow_manager_service.delete_deployment_workflows(self.json["deployment_id"])
        # TODO client should send ARN to server

        self.write({
            "success": True,
            "result": teardown_operation_results
        })

    @gen.coroutine
    def _append_transition_arns(self, deployment_id, teardown_nodes):
        deployment = self.db_session_maker.query(Deployment).filter_by(
            id=deployment_id
        ).first()

        if not deployment:
            return

        deploy_info = json.loads(deployment.deployment_json) or {}
        transition_handlers = deploy_info.get('transition_handlers', {})

        for arn in transition_handlers.values():
            teardown_nodes.append({
                "type": "lambda",
                "name": arn,
                "id": arn,
                "arn": arn
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
    def __init__(self, lambda_manager, api_gateway_manager, schedule_trigger_manager, sns_manager, sqs_manager, workflow_manager_service, aws_client_factory):
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
    aws_client_factory = None
    workflow_manager_service: WorkflowManagerService = None

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

    @gen.coroutine
    def rollback_deployment(self, deployment_diagram, credentials, exceptions, code=None, msg=None):
        self.logger("We are now rolling back the deployments we've made...", "error")

        yield self.cleanup_deployment(deployment_diagram, credentials, successful_deploy=False)

        self.logger("We've completed our rollback, returning an error...", "error")

        if code is not None:
            self.write({
                "success": False,
                "code": code,
                "msg": msg
            })
            raise gen.Return()

        self.write({
            "success": True,  # Success meaning we caught it
            "result": {
                "deployment_success": False,
                "exceptions": exceptions
            }
        })

    @authenticated
    @disable_on_overdue_payment
    @gen.coroutine
    def do_diagram_deployment(self, project_name, project_id, diagram_data, project_config, force_redeploy):
        credentials = self.get_authenticated_user_cloud_configuration()

        latest_deployment = self.dbsession.query(Deployment).filter_by(
            project_id=project_id
        ).order_by(
            Deployment.timestamp.desc()
        ).first()

        latest_deployment_json = None
        if not force_redeploy and latest_deployment is not None:
            latest_deployment_json = json.loads(latest_deployment.deployment_json)

        # Model a deployment in memory to handle the deployment of each state
        deployment_diagram: AwsDeployment = AwsDeployment(
            project_id,
            project_name,
            project_config,
            self.task_spawner,
            credentials,
            app_config=self.app_config,
            aws_client_factory=self.aws_client_factory,
            api_gateway_manager=self.api_gateway_manager,
            latest_deployment=latest_deployment_json
        )

        exceptions = yield deployment_diagram.deploy_diagram(diagram_data)

        # Check if the deployment failed
        if len(exceptions) != 0:
            yield self.rollback_deployment(deployment_diagram, credentials, [e.serialize() for e in exceptions])
            raise gen.Return()

        # Cleanup any unused resources
        try:
            yield self.cleanup_deployment(deployment_diagram, credentials, successful_deploy=True)
        except Exception as e:
            # Errors collected during cleanup should be non-blocking for a deployment
            self.logger("An error occurred while cleaning up deployment: " + str(e), "error")

        serialized_deployment = deployment_diagram.serialize()
        org = self.get_authenticated_user_org()

        # Add log bucket for the workflow manager to log to
        workflow_manager_serialized_deployment = {
            **serialized_deployment,
            "logs_bucket": credentials["logs_bucket"],
            "account_id": credentials["account_id"]
        }

        try:
            yield self.workflow_manager_service.create_workflows_for_deployment(workflow_manager_serialized_deployment)
        except WorkflowManagerException as e:
            self.logger("An error occurred while trying to create workflows in the Workflow Manager: " + str(e), "error")

            yield self.rollback_deployment(deployment_diagram, credentials, [str(e)])

            raise gen.Return()

        # TODO: Update the project data? Deployments should probably be an explicit "Save Project" action.

        # Add a reference to this deployment from the associated project
        existing_project = self.dbsession.query(Project).filter_by(
            id=project_id
        ).first()

        if existing_project is None:
            yield self.rollback_deployment(
                deployment_diagram,
                credentials,
                [],
                code="DEPLOYMENT_UPDATE",
                msg="Unable to find project when updating deployment information."
            )

            raise gen.Return()

        new_deployment = Deployment(id=deployment_diagram.deployment_id)
        new_deployment.organization_id = org.id
        new_deployment.project_id = project_id
        new_deployment.deployment_json = json.dumps(
           serialized_deployment
        )

        existing_project.deployments.append(
            new_deployment
        )

        deployment_log = DeploymentLog()
        deployment_log.org_id = org.id

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

        version_token = self.json["version_token"]

        if version_token != '5e92c868':
            self.write({
                "success": False,
                "error": "Attempted deploy with old client-side code. Please refresh your bundle and include the "
                         "proper 'version_token'."
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
