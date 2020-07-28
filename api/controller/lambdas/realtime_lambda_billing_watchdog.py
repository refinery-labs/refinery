import pinject
from tornado import gen

from assistants.aws_account_management.account_freezer import AwsAccountFreezer
from assistants.aws_account_management.account_pool_manager import is_free_tier_account
from assistants.aws_account_management.account_usage_manager import AwsAccountUsageManager, \
    AwsAccountForUsageNotFoundException, calculate_total_gb_seconds_used
from controller.base import BaseHandler
from controller.lambdas import STORE_LAMBDA_EXECUTION_DETAILS_SCHEMA

from models.aws_accounts import AWSAccount

from utils.general import logit
from jsonschema import validate as validate_schema


class RealtimeLambdaBillingWatchdogDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, aws_account_usage_manager, aws_account_freezer):
        pass


class RealtimeLambdaBillingWatchdog(BaseHandler):
    """
    This endpoint is called from the process-incoming-lambda-execution-metadata lambda function.
        (You can find this function (from the root of this repo)
        `serverless/process-incoming-lambda-execution-metadata`.)

    All lambdas which are executed as part of a Refinery project, for all users, emit a REPORT line in their logs.

    We have each user's account configured to report their lambda's execution logs to a Cloudwatch destination
    within the root Refinery account. (Look at lambda_execution_logs_destination_arn in api's config.)

    This Cloudwatch destination is hooked up to a Kinesis stream which the above lambda function batches and reads from.

    Confusing? It should be, that is why we get big $$$.
    """

    dependencies = RealtimeLambdaBillingWatchdogDependencies
    aws_account_usage_manager: AwsAccountUsageManager = None
    aws_account_freezer: AwsAccountFreezer = None

    @gen.coroutine
    def process_lambda_execution_reports(self, account_id, lambda_execution_reports):
        # First pull the relevant AWS account
        aws_account = self.dbsession.query(AWSAccount).filter_by(
            account_id=account_id,
        ).first()
        credentials = aws_account.to_dict()
        is_free_tier_user = is_free_tier_account(self.dbsession, credentials)

        # If the user is not a free tier user, we do not need to do any real time processing
        if not is_free_tier_user:
            raise gen.Return()

        gb_seconds_used = 0
        for lambda_execution_report in lambda_execution_reports:
            billed_duration = lambda_execution_report["billed_duration"]
            memory_size = lambda_execution_report["memory_size"]

            gb_seconds_used = calculate_total_gb_seconds_used(billed_duration, memory_size)

        try:
            monthly_report = self.aws_account_usage_manager.get_or_create_lambda_monthly_report(
                self.dbsession,
                account_id,
                gb_seconds_used
            )
        except AwsAccountForUsageNotFoundException:
            logit(f"Received Lambda execution data for an AWS account we don't have a record of {account_id}. Ignoring it.")
            raise gen.Return()

        # Pull their free-tier status
        usage_info = self.aws_account_usage_manager.get_aws_usage_data(
            is_free_tier_user,
            monthly_report
        )

        # If the user is not over their limit, then we do not need to freeze their account
        if not usage_info.is_over_limit:
            raise gen.Return()

        logit(f"User {account_id} is over their free-tier limit! Limiting their account...")

        yield self.aws_account_freezer.handle_user_over_limit(credentials)

    @gen.coroutine
    def post(self):
        """
        The inbound JSON POST data is the following format:
        [
            {
              "account_id": "956509444157",
              "log_name": "/aws/lambda/ayylmao_RFNzCKWzW0",
              "log_stream": "2020/02/13/[$LATEST]1095083dde2e442286e0586fa06cdcb9",
              "lambda_name": "ayylmao_RFNzCKWzW0",
              "raw_line": "REPORT RequestId: 4ae7bd66-84d5-44db-93f5-b52f4323926e\tDuration: 1091.32 ms\tBilled Duration: 1800 ms\tMemory Size: 576 MB\tMax Memory Used: 124 MB\tInit Duration: 698.39 ms\t\n",
              "timestamp": 1581635332,
              "timestamp_ms": 1581635332750,
              "duration": "1091.32",
              "memory_size": 576,
              "max_memory_used": 124,
              "billed_duration": 1800,
              "report_requestid": "4ae7bd66-84d5-44db-93f5-b52f4323926e"
            },
            ...
        ]
        """

        validate_schema(self.json, STORE_LAMBDA_EXECUTION_DETAILS_SCHEMA)

        for account_id, lambda_execution_reports in self.json.items():
            self.process_lambda_execution_reports(account_id, lambda_execution_reports)

        self.write({
            "success": True
        })
