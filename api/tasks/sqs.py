from __future__ import annotations

from time import sleep

from typing import TYPE_CHECKING

from utils.general import get_safe_workflow_state_name, logit

if TYPE_CHECKING:
    from assistants.deployments.diagram.trigger_workflow_states import SqsQueueWorkflowState


def create_sqs_queue(aws_client_factory, credentials, sqs_queue_state: SqsQueueWorkflowState):
    sqs_client = aws_client_factory.get_aws_client(
        "sqs",
        credentials
    )

    sqs_queue_name = get_safe_workflow_state_name(sqs_queue_state.name)

    queue_deleted = False
    while not queue_deleted:
        try:
            sqs_response = sqs_client.create_queue(
                QueueName=sqs_queue_name,
                Attributes={
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

    response = lambda_client.create_event_source_mapping(
        EventSourceArn=sqs_node.arn,
        FunctionName=next_node.arn,
        Enabled=True,
        BatchSize=sqs_node.batch_size,
    )

    return response


def get_sqs_existence_info(aws_client_factory, credentials, sqs_object):
    sqs_client = aws_client_factory.get_aws_client(
        "sqs",
        credentials,
    )

    try:
        queue_url_response = sqs_client.get_queue_url(
            QueueName=sqs_object.name,
        )
    except sqs_client.exceptions.QueueDoesNotExist:
        return False

    return True
