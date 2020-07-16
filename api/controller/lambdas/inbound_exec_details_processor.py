import pinject
import pystache
from tornado import gen
from controller.base import BaseHandler
from controller.lambdas import STORE_LAMBDA_EXECUTION_DETAILS_SCHEMA

from models.aws_accounts import AWSAccount
from models.users import User, RefineryUserTier
from models.lambda_executions import LambdaExecutions

from utils.general import logit
from sqlalchemy.exc import IntegrityError
from jsonschema import validate as validate_schema


class StoreLambdaExecutionDetailsDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, usage_spawner, aws_account_freezer):
        pass


class StoreLambdaExecutionDetails(BaseHandler):
    dependencies = StoreLambdaExecutionDetailsDependencies
    usage_spawner = None
    aws_account_freezer = None

    @gen.coroutine
    def post(self):
        """
        The inbound JSON POST data is the following format:
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
        }
        """

        validate_schema(self.json, STORE_LAMBDA_EXECUTION_DETAILS_SCHEMA)

        new_execution = LambdaExecutions()
        new_execution.account_id = self.json["account_id"]
        new_execution.log_name = self.json["log_name"]
        new_execution.log_stream = self.json["log_stream"]
        new_execution.lambda_name = self.json["lambda_name"]
        new_execution.raw_line = self.json["raw_line"]
        new_execution.execution_timestamp = self.json["timestamp"]
        new_execution.execution_timestamp_ms = self.json["timestamp_ms"]
        new_execution.duration = float(self.json["duration"])
        new_execution.memory_size = self.json["memory_size"]
        new_execution.max_memory_used = self.json["max_memory_used"]
        new_execution.billed_duration = self.json["billed_duration"]
        new_execution.report_requestid = self.json["report_requestid"]
        self.dbsession.add(new_execution)

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

        # First pull the relevant AWS account
        aws_account = self.dbsession.query(AWSAccount).filter_by(
            account_id=self.json["account_id"],
        ).first()
        credentials = aws_account.to_dict()

        # Pull their free-tier status
        free_tier_info = yield self.usage_spawner.get_usage_data(
            credentials
        )

        # If they've hit their free-tier limit we have to limit
        # their ability to deploy and freeze all of their current
        # Lambdas that they've deployed.
        if free_tier_info.is_over_limit:
            logit("User " + self.json["account_id"] + " is over their free-tier limit! Limiting their account...")

            # Kick off account freezer since user is over their limit
            yield self.aws_account_freezer.freeze_aws_account(
                credentials
            )

            # Send an email to the user explaining the situation
            user_emails = []
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

        self.write({
            "success": True
        })
