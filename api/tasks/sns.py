from uuid import uuid4

from utils.general import get_safe_workflow_state_name


def get_sns_topic_endpoints(aws_client_factory, credentials, sns_object):
    sns_client = aws_client_factory.get_aws_client(
        "sns",
        credentials
    )

    endpoint_arns = []

    try:
        response = sns_client.get_topic_attributes(
            TopicArn=sns_object.arn
        )

        topic_arn = response["TopicArn"]

        next_token = None
        while True:
            response = sns_client.list_subscriptions_by_topic(
                TopicArn=topic_arn,
                NextToken=next_token
            )

            subscriptions = response["Subscriptions"]
            endpoint_arns.extend([subscription["Endpoint"] for subscription in subscriptions])

            next_token = response.get("NextToken")
            if next_token is None:
                break

    except sns_client.exceptions.NotFoundException:
        return {
            "exists": False,
            "endpoints": []
        }

    return {
        "exists": True,
        "endpoints": endpoint_arns
    }


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


def subscribe_lambda_to_sns_topic(aws_client_factory, credentials, topic_object, lambda_object):
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
        FunctionName=lambda_object.arn,
        StatementId=str(uuid4()),
        Action="lambda:*",
        Principal="sns.amazonaws.com",
        SourceArn=topic_object.arn,
        # SourceAccount=self.app_config.get( "aws_account_id" ) # THIS IS A BUG IN AWS NEVER PASS THIS
    )

    sns_topic_response = sns_client.subscribe(
        TopicArn=topic_object.arn,
        Protocol="lambda",
        Endpoint=lambda_object.arn,
        Attributes={},
        ReturnSubscriptionArn=True
    )

    return {
        "statement": lambda_permission_add_response["Statement"],
        "arn": sns_topic_response["SubscriptionArn"]
    }
