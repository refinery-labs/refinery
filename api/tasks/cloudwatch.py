from json import dumps, loads
from re import sub


def automatically_fix_schedule_expression(schedule_expression):
    # Trim whitespace
    schedule_expression = schedule_expression.strip()

    # The known bad cases we want to auto-fix
    known_bad_cases = [
        "rate(1 minutes)",
        "rate(1 hours)",
        "rate(1 days)",
    ]

    if schedule_expression in known_bad_cases:
        return sub(
            "s\)$",
            ")",
            schedule_expression
        )

    # Check if they're doing the explicitly-correct non-plural case
    # If so we can just return it as-is
    for known_bad_case in known_bad_cases:
        if schedule_expression == known_bad_case.replace("s)", ")"):
            return schedule_expression

    # Outside of the above cases it should always be plural
    if not (schedule_expression.endswith("s)")):
        return sub(
            "\)$",
            "s)",
            schedule_expression
        )

    return schedule_expression


def create_cloudwatch_group(aws_client_factory, credentials, group_name, tags_dict, retention_days):
    # Create S3 client
    cloudwatch_logs = aws_client_factory.get_aws_client(
        "logs",
        credentials
    )

    response = cloudwatch_logs.create_log_group(
        logGroupName=group_name,
        tags=tags_dict
    )

    retention_response = cloudwatch_logs.put_retention_policy(
        logGroupName=group_name,
        retentionInDays=retention_days
    )

    return {
        "group_name": group_name,
        "tags_dict": tags_dict
    }


def create_cloudwatch_rule(aws_client_factory, credentials, id, name, schedule_expression, description, input_string):
    events_client = aws_client_factory.get_aws_client(
        "events",
        credentials,
    )

    schedule_expression = automatically_fix_schedule_expression(schedule_expression)

    # Events role ARN is able to be generated off of the account ID
    # The role name should be the same for all accounts.
    events_role_arn = "arn:aws:iam::" + \
        str(credentials["account_id"]) + \
        ":role/refinery_default_aws_cloudwatch_role"

    response = events_client.put_rule(
        Name=name,
        # cron(0 20 * * ? *) or rate(5 minutes)
        ScheduleExpression=schedule_expression,
        State="ENABLED",
        Description=description,
        RoleArn=events_role_arn
    )

    rule_arn = response["RuleArn"]

    tag_add_response = events_client.tag_resource(
        ResourceARN=rule_arn,
        Tags=[
            {
                "Key": "RefineryResource",
                "Value": "true"
            },
        ]
    )

    return {
        "id": id,
        "name": name,
        "arn": rule_arn,
        "input_string": input_string,
    }


def add_rule_target(aws_client_factory, credentials, rule_name, target_id, target_arn, input_string):
    # Automatically parse JSON
    try:
        input_string = loads(input_string)
    except:
        pass

    events_client = aws_client_factory.get_aws_client(
        "events",
        credentials,
    )

    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials,
    )

    targets_data = {
        "Id": target_id,
        "Arn": target_arn,
        "Input": dumps(input_string)
    }

    rule_creation_response = events_client.put_targets(
        Rule=rule_name,
        Targets=[
            targets_data
        ]
    )

    """
    For AWS Lambda you need to add a permission to the Lambda function itself
    via the add_permission API call to allow invocation via the CloudWatch event.
    """
    lambda_permission_add_response = lambda_client.add_permission(
        FunctionName=target_arn,
        StatementId=rule_name + "_statement",
        Action="lambda:*",
        Principal="events.amazonaws.com",
        SourceArn="arn:aws:events:" +
        credentials["region"] + ":" +
        str(credentials["account_id"]) + ":rule/" + rule_name,
        # SourceAccount=self.app_config.get( "aws_account_id" ) # THIS IS A BUG IN AWS NEVER PASS THIS
    )

    return rule_creation_response


def get_cloudwatch_existence_info(aws_client_factory, credentials, _id, _type, name):
    events_client = aws_client_factory.get_aws_client(
        "events",
        credentials
    )

    try:
        response = events_client.describe_rule(
            Name=name,
        )
    except events_client.exceptions.ResourceNotFoundException:
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
        "arn": response["Arn"],
        "exists": True,
    }


