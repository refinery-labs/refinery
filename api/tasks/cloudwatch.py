from json import dumps, loads
from re import sub
from time import sleep
from utils.general import logit


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
            r"s\)$",
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
            r"\)$",
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


def create_cloudwatch_rule(aws_client_factory, credentials, cloudwatch_rule):
    events_client = aws_client_factory.get_aws_client(
        "events",
        credentials,
    )

    schedule_expression = automatically_fix_schedule_expression(cloudwatch_rule.schedule_expression)

    # Events role ARN is able to be generated off of the account ID
    # The role name should be the same for all accounts.

    response = events_client.put_rule(
        Name=cloudwatch_rule.name,
        # cron(0 20 * * ? *) or rate(5 minutes)
        ScheduleExpression=schedule_expression,
        State="ENABLED",
        Description=cloudwatch_rule.description,
        RoleArn=cloudwatch_rule.events_role_arn
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

    cloudwatch_rule.arn = rule_arn

    return {
        "id": cloudwatch_rule.id,
        "name": cloudwatch_rule.name,
        "arn": cloudwatch_rule.arn,
        "input_string": cloudwatch_rule.input_string,
    }


def add_rule_target(aws_client_factory, credentials, rule, target):
    events_client = aws_client_factory.get_aws_client(
        "events",
        credentials,
    )

    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials,
    )

    targets_data = {
        "Id": target.name,
        "Arn": target.arn,
        "Input": rule.input_string
    }

    rule_creation_response = events_client.put_targets(
        Rule=rule.name,
        Targets=[
            targets_data
        ]
    )

    """
    For AWS Lambda you need to add a permission to the Lambda function itself
    via the add_permission API call to allow invocation via the CloudWatch event.
    """
    lambda_permission_add_response = lambda_client.add_permission(
        FunctionName=target.arn,
        StatementId=rule.name + "_statement",
        Action="lambda:*",
        Principal="events.amazonaws.com",
        SourceArn=rule.arn,
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


def get_lambda_cloudwatch_logs(aws_client_factory, credentials, log_group_name, stream_id):
    cloudwatch_logs_client = aws_client_factory.get_aws_client(
        "logs",
        credentials
    )

    if not stream_id:
        # Pull the last stream from CloudWatch
        # Streams take time to propagate so wait if needed
        streams_data = cloudwatch_logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy="LastEventTime",
            limit=50
        )

        stream_id = streams_data["logStreams"][0]["logStreamName"]

    log_output = ""
    attempts_remaining = 4
    some_log_data_returned = False
    forward_token = False
    last_forward_token = False

    while attempts_remaining > 0:
        logit("[ STATUS ] Grabbing log events from '" +
              log_group_name + "' at '" + stream_id + "'...")
        get_log_events_params = {
            "logGroupName": log_group_name,
            "logStreamName": stream_id
        }

        if forward_token:
            get_log_events_params["nextToken"] = forward_token

        log_data = cloudwatch_logs_client.get_log_events(
            **get_log_events_params
        )

        last_forward_token = forward_token
        forward_token = False
        forward_token = log_data["nextForwardToken"]

        # If we got nothing in response we'll try again
        if len(log_data["events"]) == 0 and some_log_data_returned == False:
            attempts_remaining = attempts_remaining - 1
            sleep(1)
            continue

        # If that's the last of the log data, quit out
        if last_forward_token == forward_token:
            break

        # Indicate we've at least gotten some log data previously
        some_log_data_returned = True

        for event_data in log_data["events"]:
            # Append log data
            log_output += event_data["message"]

    return log_output
