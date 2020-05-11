from time import sleep

from utils.general import get_safe_workflow_state_name, logit


def create_sqs_queue(aws_client_factory, credentials, id, queue_name, batch_size, visibility_timeout):
    sqs_client = aws_client_factory.get_aws_client(
        "sqs",
        credentials
    )

    sqs_queue_name = get_safe_workflow_state_name(queue_name)

    queue_deleted = False

    while queue_deleted == False:
        try:
            sqs_response = sqs_client.create_queue(
                QueueName=sqs_queue_name,
                Attributes={
                    "DelaySeconds": str(0),
                    "MaximumMessageSize": "262144",
                    # Lambda max time plus ten seconds
                    "VisibilityTimeout": str(visibility_timeout),
                }
            )

            queue_deleted = True
        except sqs_client.exceptions.QueueDeletedRecently:
            logit(
                "SQS queue was deleted too recently, trying again in ten seconds...")

            sleep(10)

    sqs_arn = "arn:aws:sqs:" + \
        credentials["region"] + ":" + \
        str(credentials["account_id"]) + ":" + queue_name
    sqs_url = "https://sqs." + \
        credentials["region"] + ".amazonaws.com/" + \
        str(credentials["account_id"]) + "/" + queue_name

    sqs_tag_queue_response = sqs_client.tag_queue(
        QueueUrl=sqs_url,
        Tags={
            "RefineryResource": "true"
        }
    )

    return {
        "id": id,
        "name": queue_name,
        "arn": sqs_arn,
        "batch_size": batch_size
    }


def map_sqs_to_lambda(aws_client_factory, credentials, sqs_arn, lambda_arn, batch_size):
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    response = lambda_client.create_event_source_mapping(
        EventSourceArn=sqs_arn,
        FunctionName=lambda_arn,
        Enabled=True,
        BatchSize=batch_size,
    )

    return response


def get_sqs_existence_info(aws_client_factory, credentials, _id, _type, name):
    sqs_client = aws_client_factory.get_aws_client(
        "sqs",
        credentials,
    )

    try:
        queue_url_response = sqs_client.get_queue_url(
            QueueName=name,
        )
    except sqs_client.exceptions.QueueDoesNotExist:
        return {
            "id": _id,
            "type": _type,
            "name": name,
            "exists": False
        }

    return {
        "id": _id,
        "type": _type,
        "name": name,
        "arn": "arn:aws:sqs:" + credentials["region"] + ":" + str(credentials["account_id"]) + ":" + name,
        "exists": True,
    }
