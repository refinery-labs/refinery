import json

from jsonschema import validate as validate_schema
from tornado import gen

from controller import BaseHandler
from controller.decorators import authenticated, disable_on_overdue_payment
from controller.lambdas.actions import is_build_package_cached
from controller.lambdas.schemas import *
from models import Deployment


class RunLambda(BaseHandler):
    @authenticated
    @disable_on_overdue_payment
    @gen.coroutine
    def post(self):
        """
        Run a Lambda which has been deployed in production.
        """
        validate_schema(self.json, RUN_LAMBDA_SCHEMA)

        self.logger("Running Lambda with ARN of '" + self.json["arn"] + "'...")

        credentials = self.get_authenticated_user_cloud_configuration()

        backpack_data = {}
        input_data = self.json["input_data"]

        if "backpack" in self.json:
            # Try to parse backpack as JSON
            try:
                backpack_data = json.loads(
                    self.json["backpack"]
                )
            except ValueError:
                self.write({
                    "success": False,
                    "failure_msg": "Unable to read backpack data JSON",
                    "failure_reason": "InvalidBackpackJson"
                })
                return

        # Try to parse Lambda input as JSON
        try:
            input_data = json.loads(
                self.json["input_data"]
            )
        except ValueError:
            pass

        lambda_input_data = {
            "_refinery": {
                "backpack": backpack_data,
                "throw_exceptions_fully": True,
                "input_data": input_data
            }
        }

        if "execution_id" in self.json and self.json["execution_id"]:
            lambda_input_data["_refinery"]["execution_id"] = str(self.json["execution_id"])

        if "debug_id" in self.json:
            lambda_input_data["_refinery"]["live_debug"] = {
                "debug_id": self.json["debug_id"],
                "websocket_uri": self.app_config.get("LAMBDA_CALLBACK_ENDPOINT"),
            }

        self.logger("Executing Lambda...")
        lambda_result = yield self.task_spawner.execute_aws_lambda(
            credentials,
            self.json["arn"],
            lambda_input_data
        )

        self.write({
            "success": True,
            "result": lambda_result
        })


class GetCloudWatchLogsForLambda(BaseHandler):
    @authenticated
    @disable_on_overdue_payment
    @gen.coroutine
    def post(self):
        """
        Get CloudWatch Logs for a given Lambda ARN.

        The logs may not be complete, since it takes time to propogate.
        """
        validate_schema(self.json, GET_CLOUDWATCH_LOGS_FOR_LAMBDA_SCHEMA)

        self.logger("Retrieving CloudWatch logs...")

        credentials = self.get_authenticated_user_cloud_configuration()

        arn = self.json["arn"]
        arn_parts = arn.split(":")
        lambda_name = arn_parts[-1]
        log_group_name = "/aws/lambda/" + lambda_name

        log_output = yield self.task_spawner.get_lambda_cloudwatch_logs(
            credentials,
            log_group_name,
            False
        )

        truncated = True

        if "END RequestId: " in log_output:
            truncated = False

        self.write({
            "success": True,
            "result": {
                "truncated": truncated,
                "log_output": log_output
            }
        })


class UpdateEnvironmentVariables(BaseHandler):
    @authenticated
    @disable_on_overdue_payment
    @gen.coroutine
    def post(self):
        """
        Update environment variables for a given Lambda.

        Save the updated deployment diagram to the database and return
        it to the frontend.
        """
        validate_schema(self.json, UPDATE_ENVIRONMENT_VARIABLES_SCHEMA)

        self.logger("Updating environment variables...")

        credentials = self.get_authenticated_user_cloud_configuration()

        response = yield self.task_spawner.update_lambda_environment_variables(
            credentials,
            self.json["arn"],
            self.json["environment_variables"],
        )

        # Update the deployment diagram to reflect the new environment variables
        latest_deployment = self.dbsession.query(Deployment).filter_by(
            project_id=self.json["project_id"]
        ).order_by(
            Deployment.timestamp.desc()
        ).first()

        # Get deployment diagram from it
        deployment_diagram_data = json.loads(latest_deployment.deployment_json)

        # Get node with the specified ARN and update it
        for workflow_state in deployment_diagram_data["workflow_states"]:
            if workflow_state["arn"] == self.json["arn"]:
                workflow_state["environment_variables"] = self.json["environment_variables"]

        latest_deployment.deployment_json = json.dumps(deployment_diagram_data)
        self.dbsession.commit()

        self.write({
            "success": True,
            "result": {
                "deployment_diagram": deployment_diagram_data
            }
        })


class BuildLibrariesPackage(BaseHandler):
    builder_manager = None

    def _initialize(self, builder_manager):
        self.builder_manager = builder_manager

    @authenticated
    @gen.coroutine
    def post(self):
        """
        Kick off a codebuild for listed build libraries.
        """
        validate_schema(self.json, BUILD_LIBRARIES_PACKAGE_SCHEMA)

        current_user = self.get_authenticated_user()
        credentials = self.get_authenticated_user_cloud_configuration()

        # TODO just accept a dict/object in of an
        # array followed by converting it to one.
        libraries_dict = {}
        for library in self.json["libraries"]:
            libraries_dict[str(library)] = "latest"

        build_id = False

        # Get the final S3 path
        final_s3_package_zip_path = yield self.task_spawner.get_final_zip_package_path(
            self.json["language"],
            libraries_dict,
        )

        if self.json["language"] == "python2.7":
            build_id = yield self.task_spawner.start_python27_codebuild(
                credentials,
                libraries_dict
            )
        elif self.json["language"] == "python3.6":
            build_id = yield self.task_spawner.start_python36_codebuild(
                credentials,
                libraries_dict
            )
        elif self.json["language"] == "nodejs8.10":
            build_id = yield self.task_spawner.start_node810_codebuild(
                credentials,
                libraries_dict
            )
        elif self.json["language"] == "nodejs10.16.3":
            build_id = yield self.task_spawner.start_node10163_codebuild(
                credentials,
                libraries_dict
            )
        elif self.json["language"] == "nodejs10.20.1":
            build_id = yield self.task_spawner.start_node10201_codebuild(
                credentials,
                libraries_dict
            )
        elif self.json["language"] == "php7.3":
            build_id = yield self.task_spawner.start_php73_codebuild(
                credentials,
                libraries_dict
            )
        elif self.json["language"] == "ruby2.6.4":
            build_id = yield self.task_spawner.start_ruby264_codebuild(
                credentials,
                libraries_dict
            )
        elif self.json["language"] == "go1.12":
            # We spin up our ECS task to get this going.
            # Don't yield here, we don't care about the result
            self.logger("Heating up the Build Container...")
            self.builder_manager.get_build_container_ip(
                credentials
            )
        else:
            self.error(
                "You've provided a language that Refinery does not currently support!",
                "UNSUPPORTED_LANGUAGE"
            )
            raise gen.Return()

        if build_id:
            # Don't yield here because we don't care about the outcome of this task
            # we just want to kick it off in the background
            self.task_spawner.finalize_codebuild(
                credentials,
                build_id,
                final_s3_package_zip_path
            )

        self.write({
            "success": True,
        })


class CheckIfLibrariesCached(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Just returns if a given language + libraries has
        already been built and cached in S3.
        """
        validate_schema(self.json, CHECK_IF_LIBRARIES_CACHED_SCHEMA)

        credentials = self.get_authenticated_user_cloud_configuration()

        is_already_cached = yield is_build_package_cached(
            self.task_spawner,
            credentials,
            self.json["language"],
            self.json["libraries"]
        )

        self.write({
            "success": True,
            "is_already_cached": is_already_cached,
        })
