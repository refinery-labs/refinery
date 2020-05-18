from uuid import uuid4

from utils.general import get_safe_workflow_state_name


def get_sns_existence_info(aws_client_factory, credentials, sns_object):
    sns_client = aws_client_factory.get_aws_client(
        "sns",
        credentials
    )

    try:
        response = sns_client.get_topic_attributes(
            TopicArn=sns_object.arn
        )
    except sns_client.exceptions.NotFoundException:
        return False

    return True


def create_sns_topic(aws_client_factory, credentials, id, topic_name):
    sns_client = aws_client_factory.get_aws_client(
        "sns",
        credentials
    )

    topic_name = get_safe_workflow_state_name(topic_name)
    response = sns_client.create_topic(
        Name=topic_name,
        Tags=[
            {
                "Key": "RefineryResource",
                "Value": "true"
            },
        ]
    )

    return {
        "id": id,
        "name": topic_name,
        "arn": response["TopicArn"]
    }


def subscribe_lambda_to_sns_topic(aws_client_factory, credentials, topic_arn, lambda_arn):
    """
    For AWS Lambda you need to add a permission to the Lambda function itself
    via the add_permission API call to allow invocation via the SNS event.
    """
    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    sns_client = aws_client_factory.get_aws_client(
        "sns",
        credentials,
    )

    lambda_permission_add_response = lambda_client.add_permission(
        FunctionName=lambda_arn,
        StatementId=str(uuid4()),
        Action="lambda:*",
        Principal="sns.amazonaws.com",
        SourceArn=topic_arn,
        # SourceAccount=self.app_config.get( "aws_account_id" ) # THIS IS A BUG IN AWS NEVER PASS THIS
    )

    sns_topic_response = sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol="lambda",
        Endpoint=lambda_arn,
        Attributes={},
        ReturnSubscriptionArn=True
    )

    return {
        "statement": lambda_permission_add_response["Statement"],
        "arn": sns_topic_response["SubscriptionArn"]
    }
