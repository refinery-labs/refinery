from __future__ import annotations

from time import sleep

from typing import TYPE_CHECKING

from utils.general import get_safe_workflow_state_name, logit
from utils.wrapped_aws_functions import sqs_get_queue_url, lambda_create_event_source_mapping, sqs_create_queue

if TYPE_CHECKING:
    from assistants.deployments.aws.sqs_queue import SqsQueueWorkflowState


def create_sqs_queue(aws_client_factory, credentials, sqs_queue_state: SqsQueueWorkflowState):
    sqs_client = aws_client_factory.get_aws_client(
        "sqs",
        credentials
    )

    sqs_queue_name = get_safe_workflow_state_name(sqs_queue_state.name)

    queue_deleted = False
    while not queue_deleted:
        try:
            sqs_response = sqs_create_queue(
                sqs_client,
                queue_name=sqs_queue_name,
                attributes={
                    "DelaySeconds": str(0),
                    "MaximumMessageSize": "262144",
                    # Lambda max time plus ten seconds
                    "VisibilityTimeout": str(sqs_queue_state.visibility_timeout),
                }
            )

            queue_deleted = True
        except sqs_client.exceptions.QueueDeletedRecently:
            logit(
                "SQS queue was deleted too recently, trying again in ten seconds...")

            sleep(10)

    sqs_tag_queue_response = sqs_client.tag_queue(
        QueueUrl=sqs_queue_state.url,
        Tags={
            "RefineryResource": "true"
        }
    )

    return {
        "id": id,
        "name": sqs_queue_state.name,
        "arn": sqs_queue_state.arn,
        "batch_size": sqs_queue_state.batch_size
    }


def map_sqs_to_lambda(aws_client_factory, credentials, sqs_node, next_node):
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    response = lambda_create_event_source_mapping(
        lambda_client,
        event_source_arn=sqs_node.arn,
        function_name=next_node.arn,
        enabled=True,
        batch_size=sqs_node.batch_size,
    )

    return response


def get_sqs_existence_info(aws_client_factory, credentials, sqs_object):
    sqs_client = aws_client_factory.get_aws_client(
        "sqs",
        credentials,
    )

    try:
        queue_url_response = sqs_get_queue_url(
            sqs_client,
            queue_name=sqs_object.name,
        )
    except sqs_client.exceptions.QueueDoesNotExist:
        return False

    return True
