from tornado import gen
from typing import List

from assistants.deployments.api_gateway import strip_api_gateway
from assistants.deployments.aws_pigeon.api_gateway import ApiGatewayDeploymentState
from assistants.deployments.aws_pigeon.types import AwsDeploymentState
from assistants.deployments.diagram.types import StateTypes


@gen.coroutine
def teardown_infrastructure(api_gateway_manager, lambda_manager, schedule_trigger_manager, sns_manager, sqs_manager, credentials, teardown_nodes):
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
                lambda_manager.delete_lambda(
                    credentials,
                    teardown_node["id"],
                    teardown_node["type"],
                    teardown_node["name"],
                    teardown_node["arn"],
                )
            )
        if teardown_node["type"] == "sns_topic":
            teardown_operation_futures.append(
                sns_manager.delete_sns_topic(
                    credentials,
                    teardown_node["id"],
                    teardown_node["type"],
                    teardown_node["name"],
                    teardown_node["arn"],
                )
            )
        elif teardown_node["type"] == "sqs_queue":
            teardown_operation_futures.append(
                sqs_manager.delete_sqs_queue(
                    credentials,
                    teardown_node["id"],
                    teardown_node["type"],
                    teardown_node["name"],
                    teardown_node["arn"],
                )
            )
        elif teardown_node["type"] == "schedule_trigger" or teardown_node["type"] == "warmer_trigger":
            teardown_operation_futures.append(
                schedule_trigger_manager.delete_schedule_trigger(
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
                    api_gateway_manager,
                    credentials,
                    teardown_node["rest_api_id"],
                )
            )

    teardown_operation_results = yield teardown_operation_futures

    raise gen.Return(teardown_operation_results)


@gen.coroutine
def teardown_deployed_states(api_gateway_manager, lambda_manager, schedule_trigger_manager, sns_manager, sqs_manager, credentials, teardown_nodes: List[AwsDeploymentState]):
    teardown_operation_futures = []

    # TODO refactor teardown functions so that they only take have the necessary info

    for teardown_node in teardown_nodes:
        if teardown_node.type == StateTypes.LAMBDA or teardown_node.type == StateTypes.API_ENDPOINT:
            teardown_operation_futures.append(
                lambda_manager.delete_lambda(
                    credentials,
                    None, None, teardown_node.name, teardown_node.arn
                )
            )
        if teardown_node.type == StateTypes.SNS_TOPIC:
            teardown_operation_futures.append(
                sns_manager.delete_sns_topic(
                    credentials,
                    None, None, None,
                    teardown_node.arn
                )
            )
        elif teardown_node.type == StateTypes.SQS_QUEUE:
            teardown_operation_futures.append(
                sqs_manager.delete_sqs_queue(
                    credentials,
                    None, None, None,
                    teardown_node.arn
                )
            )
        elif teardown_node.type == StateTypes.SCHEDULE_TRIGGER or teardown_node.type == StateTypes.WARMER_TRIGGER:
            teardown_operation_futures.append(
                schedule_trigger_manager.delete_schedule_trigger(
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
                    api_gateway_manager,
                    credentials,
                    teardown_node.api_gateway_id,
                )
            )

    teardown_operation_results = yield teardown_operation_futures

    raise gen.Return(teardown_operation_results)
