import datetime

import pinject
import pystache
from dateutil import relativedelta
from tornado import gen
from typing import Union

from assistants.aws_account_management.account_freezer import AwsAccountFreezer
from assistants.billing.billing_assistant import BillingSpawner
from controller.base import BaseHandler
from controller.lambdas import STORE_LAMBDA_EXECUTION_DETAILS_SCHEMA

from models.aws_accounts import AWSAccount
from models.users import User, RefineryUserTier
from models.lambda_execution_monthly_report import LambdaExecutionMonthlyReport

from utils.general import logit
from sqlalchemy.exc import IntegrityError
from jsonschema import validate as validate_schema


class AwsUsageData:
    def __init__(
            self,
            gb_seconds=0.0,
            remaining_gb_seconds=0,
            executions=0,
            is_over_limit=False
    ):
        self.gb_seconds = gb_seconds
        self.remaining_gb_seconds = remaining_gb_seconds
        self.executions = executions
        self.is_over_limit = is_over_limit

    def serialize(self):
        return {
            "gb_seconds": self.gb_seconds,
            "remaining_gb_seconds": self.remaining_gb_seconds,
            "executions": self.executions,
            "is_over_limit": self.is_over_limit,
        }

    def __str__(self):
        return str(self.serialize())


def get_first_day_of_month():
    today = datetime.date.today()
    if today.day > 25:
        today += datetime.timedelta(7)
    return today.replace(day=1)


def get_first_day_of_next_month():
    first_day_of_month = get_first_day_of_month()

    return first_day_of_month + relativedelta.relativedelta(months=1)


def calculate_total_gb_seconds_used(billed_exec_duration_ms, billed_exec_mb):
    # Get fraction of GB-second and multiply it by
    # the billed execution to get the total GB-seconds
    # used in milliseconds.
    gb_fraction = 1024 / billed_exec_mb
    return (gb_fraction * billed_exec_duration_ms) / 1000


def calculate_remaining_gb_seconds(is_free_tier_user, max_gb_seconds, gb_seconds_used):
    # If the user is not a free tier user, then there is no cap on usage
    if not is_free_tier_user:
        return -1

    # Get the remaining free-tier GB-seconds the user has
    remaining_gb_seconds = max_gb_seconds - gb_seconds_used

    # If they've gone over the max just return zero
    if remaining_gb_seconds < 0:
        return 0

    return remaining_gb_seconds


class StoreLambdaExecutionDetailsDependencies:
    def __init__(self, app_config, aws_account_freezer):
        self.aws_account_freezer = aws_account_freezer

        # The maximum number of GB-seconds a free-tier user can use
        # before their deployments are frozen to prevent any further
        # resource usage.
        self.free_tier_monthly_max_gb_seconds = app_config.get("free_tier_monthly_max_gb_seconds")


class RealtimeBillingWatchdog(BaseHandler):
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

    dependencies = StoreLambdaExecutionDetailsDependencies
    aws_account_freezer: AwsAccountFreezer = None
    free_tier_monthly_max_gb_seconds: int = 0

    def get_aws_usage_data(self, is_free_tier_user, lambda_execution_report) -> AwsUsageData:
        remaining_gb_seconds = calculate_remaining_gb_seconds(
            is_free_tier_user,
            self.free_tier_monthly_max_gb_seconds,
            lambda_execution_report.gb_seconds_used
        )

        is_over_limit = remaining_gb_seconds == 0

        return AwsUsageData(
            gb_seconds=lambda_execution_report.gb_seconds_used,
            remaining_gb_seconds=remaining_gb_seconds,
            executions=lambda_execution_report.total_executions,
            is_over_limit=is_over_limit
        )

    def get_monthly_user_lambda_execution_report(self, account_id) -> Union[LambdaExecutionMonthlyReport, None]:
        # Get timestamp window for the beginning of this month to
        # the end of this month. We use this to filter only the
        # relevant executions for this month.
        first_day_of_month_timestamp = int(
            get_first_day_of_month().strftime("%s")
        )

        first_day_of_next_month_timestamp = int(
            get_first_day_of_next_month().strftime("%s")
        )

        lambda_execution_report: LambdaExecutionMonthlyReport = self.dbsession.query(LambdaExecutionMonthlyReport).filter_by(
            account_id=account_id
        ).filter(
            LambdaExecutionMonthlyReport.timestamp >= first_day_of_month_timestamp,
            LambdaExecutionMonthlyReport.timestamp <= first_day_of_next_month_timestamp
        ).first()

        return lambda_execution_report

    def _is_free_tier_account(self, credentials):
        # Check if the user is a MANAGED account, if not
        # then they can't be free-tier.
        if credentials[ "account_type" ] != "MANAGED":
            return False

        # Pull the organization users and check if any
        # are paid tier.
        organization_id = credentials[ "organization_id" ]

        # If there's no organization associated with the account
        # then it's free-tier by default.
        if not organization_id:
            return True

        org_users = [
            org_user
            for org_user in self.dbsession.query( User ).filter_by(
                organization_id=organization_id
            ).all()
        ]

        # Default to the user not being paid tier
        # unless we are proven differently
        is_paid_tier = False
        for org_user in org_users:
            if org_user.tier == RefineryUserTier.PAID:
                is_paid_tier = True

        is_free_tier = not is_paid_tier

        return is_free_tier

    def get_or_create_lambda_monthly_report(self, account_id, billed_duration, billed_memory_size) -> LambdaExecutionMonthlyReport:
        gb_seconds_used = calculate_total_gb_seconds_used(billed_duration, billed_memory_size)

        monthly_report = self.get_monthly_user_lambda_execution_report(account_id)

        if monthly_report is None:
            monthly_report = LambdaExecutionMonthlyReport(account_id, gb_seconds_used)
            self.dbsession.add(monthly_report)
        else:
            monthly_report.gb_seconds_used += gb_seconds_used

        monthly_report.total_executions += 1

        try:
            self.dbsession.commit()
        except IntegrityError as e:
            """
            An expected error case is when we get an execution
            for an AWS account which is no longer in the database.
            This can happen specifically for third-party AWS accounts
            which are no longer managed by us but are still sending us
            their Lambda execution data. For these instances we just
            print a line about it occurring and suppress the full
            SQL exception.
            """
            sql_error_message = str(e.orig)

            is_non_existent_aws_account = (
                    "Key (account_id)=(" in sql_error_message
                    and "is not present in table \"aws_accounts\"." in sql_error_message
            )

            if is_non_existent_aws_account:
                logit("Received Lambda execution data for an AWS account we don't have a record of (" + self.json[
                    "account_id"] + "). Ignoring it.")
                self.write({
                    "success": False
                })
                raise gen.Return()

            # If it's not a non-existent AWS account issue
            # then we'll rethrow it
            raise

        return monthly_report

    @gen.coroutine
    def handle_user_over_limit(self, credentials):
        # Kick off account freezer since user is over their limit
        yield self.aws_account_freezer.freeze_aws_account(
            credentials
        )

        # Send an email to the user explaining the situation
        organization_users = self.dbsession.query(User).filter_by(
            organization_id=credentials["organization_id"]
        ).all()
        for organization_user in organization_users:
            email_templates = self.app_config.get("EMAIL_TEMPLATES")

            yield self.task_spawner.send_email(
                organization_user.email,
                "[IMPORTANT] You've exceeded your Refinery free-tier quota!",
                False,
                pystache.render(
                    email_templates["account_frozen_alert"],
                    {
                        "name": organization_user.name
                    }
                ),
            )

    @gen.coroutine
    def process_lambda_execution_report(self, lambda_execution_report):
        account_id = lambda_execution_report["account_id"]

        # First pull the relevant AWS account
        aws_account = self.dbsession.query(AWSAccount).filter_by(
            account_id=account_id,
        ).first()
        credentials = aws_account.to_dict()
        is_free_tier_user = self._is_free_tier_account(credentials)

        is_free_tier_user = True

        # If the user is not a free tier user, we do not need to do any real time processing
        if not is_free_tier_user:
            raise gen.Return()

        billed_duration = lambda_execution_report["billed_duration"]
        memory_size = lambda_execution_report["memory_size"]

        monthly_report = self.get_or_create_lambda_monthly_report(
            account_id, billed_duration, memory_size)

        # Pull their free-tier status
        usage_info = self.get_aws_usage_data(
            is_free_tier_user,
            monthly_report
        )

        # If the user is not over their limit, then we do not need to freeze their account
        if not usage_info.is_over_limit:
            raise gen.Return()

        logit(f"User {account_id} is over their free-tier limit! Limiting their account...")

        # yield self.handle_user_over_limit(credentials)

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

        for lambda_execution_report in self.json:
            yield self.process_lambda_execution_report(lambda_execution_report)

        self.write({
            "success": True
        })
