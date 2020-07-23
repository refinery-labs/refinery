from tornado import gen
from tornado.concurrent import run_on_executor
from typing import List

from assistants.deployments.api_gateway import strip_api_gateway
from assistants.deployments.aws.api_gateway import ApiGatewayDeploymentState
from assistants.deployments.aws.types import AwsDeploymentState
from assistants.deployments.diagram.types import StateTypes
from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from utils.base_spawner import BaseSpawner
from utils.general import logit


class AwsTeardownManager(BaseSpawner):
    def __init__(
            self,
            aws_cloudwatch_client,
            logger,
            task_spawner,
            db_session_maker,
            app_config,
            api_gateway_manager,
            lambda_manager,
            schedule_trigger_manager,
            sns_manager,
            sqs_manager
    ):
        super().__init__(aws_cloudwatch_client, logger, app_config=app_config)

        self.task_spawner = task_spawner
        self.db_session_maker = db_session_maker
        self.api_gateway_manager = api_gateway_manager
        self.lambda_manager = lambda_manager
        self.schedule_trigger_manager = schedule_trigger_manager
        self.sns_manager = sns_manager
        self.sqs_manager = sqs_manager

    @gen.coroutine
    def delete_logs(self, credentials, project_id):
        for _ in range(1000):
            # Delete 1K logs at a time
            log_paths = yield self.task_spawner.get_s3_pipeline_execution_logs(
                credentials,
                project_id + "/",
                1000
            )

            logit("Deleting #" + str(len(log_paths)) + " log files for project ID " + project_id + "...")

            if len(log_paths) == 0:
                break

            yield self.task_spawner.bulk_s3_delete(
                credentials,
                credentials["logs_bucket"],
                log_paths
            )

    @run_on_executor
    def delete_api_gateway(self, credentials, project_config):
        return AwsTeardownManager._delete_api_gateway(
            self.task_spawner,
            self.api_gateway_manager,
            credentials,
            project_config
        )

    @staticmethod
    def _delete_api_gateway(logger, api_gateway_manager, credentials, project_config):
        project_config_dict = project_config["config_json"]

        # Delete the API Gateway associated with this project
        if "api_gateway" not in project_config_dict:
            raise gen.Return()

        api_gateway_id = project_config_dict["api_gateway"].get("gateway_id")

        if api_gateway_id is None:
            raise gen.Return()

        logger(f"Deleting associated API Gateway '{api_gateway_id}'...")

        yield api_gateway_manager.delete_rest_api(
            credentials,
            api_gateway_id
        )

    @gen.coroutine
    def teardown_infrastructure(self, credentials, teardown_nodes):
        """
        [
                {
                        "id": {{node_id}},
                        "arn": {{production_resource_arn}},
                        "name": {{node_name}},
                        "type": {{node_type}},
                }
        ]
        """
        teardown_operation_futures = []

        # Add an ID and "name" to nodes if not set, they are not technically
        # required and are a remnant of the old code.
        # This all needs to be refactored, but that's a much larger undertaking.
        for teardown_node in teardown_nodes:
            if not ("name" in teardown_node):
                teardown_node["name"] = teardown_node["id"]

            if not ("arn" in teardown_node):
                teardown_node["arn"] = teardown_node["id"]

        for teardown_node in teardown_nodes:
            # Skip if the node doesn't exist
            # TODO move this client side, it's silly here.
            if "exists" in teardown_node and teardown_node["exists"] == False:
                continue

            # TODO we should just pass the workflow states into here

            if teardown_node["type"] == "lambda" or teardown_node["type"] == "api_endpoint":
                teardown_operation_futures.append(
                    self.lambda_manager.delete_lambda(
                        credentials,
                        teardown_node["id"],
                        teardown_node["type"],
                        teardown_node["name"],
                        teardown_node["arn"],
                    )
                )
            if teardown_node["type"] == "sns_topic":
                teardown_operation_futures.append(
                    self.sns_manager.delete_sns_topic(
                        credentials,
                        teardown_node["id"],
                        teardown_node["type"],
                        teardown_node["name"],
                        teardown_node["arn"],
                    )
                )
            elif teardown_node["type"] == "sqs_queue":
                teardown_operation_futures.append(
                    self.sqs_manager.delete_sqs_queue(
                        credentials,
                        teardown_node["id"],
                        teardown_node["type"],
                        teardown_node["name"],
                        teardown_node["arn"],
                    )
                )
            elif teardown_node["type"] == "schedule_trigger" or teardown_node["type"] == "warmer_trigger":
                teardown_operation_futures.append(
                    self.schedule_trigger_manager.delete_schedule_trigger(
                        credentials,
                        teardown_node["id"],
                        teardown_node["type"],
                        teardown_node["name"],
                        teardown_node["arn"],
                    )
                )
            elif teardown_node["type"] == "api_gateway":
                teardown_operation_futures.append(
                    strip_api_gateway(
                        self.api_gateway_manager,
                        credentials,
                        teardown_node["rest_api_id"],
                    )
                )

        teardown_operation_results = yield teardown_operation_futures
        raise gen.Return(teardown_operation_results)

    @gen.coroutine
    def teardown_deployed_states(self, credentials, teardown_nodes: List[AwsDeploymentState]):
        teardown_operation_futures = []

        # TODO refactor teardown functions so that they only take have the necessary info

        for teardown_node in teardown_nodes:
            if teardown_node.type == StateTypes.LAMBDA or teardown_node.type == StateTypes.API_ENDPOINT:
                teardown_operation_futures.append(
                    self.lambda_manager.delete_lambda(
                        credentials,
                        None, None, teardown_node.name, teardown_node.arn
                    )
                )
            if teardown_node.type == StateTypes.SNS_TOPIC:
                teardown_operation_futures.append(
                    self.sns_manager.delete_sns_topic(
                        credentials,
                        None, None, None,
                        teardown_node.arn
                    )
                )
            elif teardown_node.type == StateTypes.SQS_QUEUE:
                teardown_operation_futures.append(
                    self.sqs_manager.delete_sqs_queue(
                        credentials,
                        None, None, None,
                        teardown_node.arn
                    )
                )
            elif teardown_node.type == StateTypes.SCHEDULE_TRIGGER or teardown_node.type == StateTypes.WARMER_TRIGGER:
                teardown_operation_futures.append(
                    self.schedule_trigger_manager.delete_schedule_trigger(
                        credentials,
                        None, None, None,
                        teardown_node.arn
                    )
                )
            elif teardown_node.type == StateTypes.API_GATEWAY:

                assert isinstance(teardown_node, ApiGatewayDeploymentState)

                if teardown_node.api_gateway_id is None:
                    continue

                teardown_operation_futures.append(
                    strip_api_gateway(
                        self.api_gateway_manager,
                        credentials,
                        teardown_node.api_gateway_id,
                    )
                )

        teardown_operation_results = yield teardown_operation_futures
        raise gen.Return(teardown_operation_results)
