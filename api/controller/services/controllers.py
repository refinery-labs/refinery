import time
from jsonschema import validate as validate_schema

import pinject
from ansi2html import Ansi2HTMLConverter
from botocore.exceptions import ClientError
from sqlalchemy import or_ as sql_or
from tornado import gen
from traceback import print_exc

from assistants.deployments.teardown import teardown_infrastructure
from controller import BaseHandler
from controller.services.actions import clear_sub_account_packages, get_last_month_start_and_end_date_strings
from exc import TerraformError
from models import AWSAccount, User, TerraformStateVersion
from assistants.deployments.dangling_resources import get_user_dangling_resources
from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME


class AdministrativeAssumeAccount(BaseHandler):
    def get(self, user_id=None):
        """
        For helping customers with their accounts.
        """
        if not user_id:
            self.write({
                "success": False,
                "msg": "You must specify a user_id via the URL (/UUID/)."
            })

        # Authenticate the user via secure cookie
        self.authenticate_user_id(
            user_id
        )

        self.redirect(
            "/"
        )


class AssumeRoleCredentials(BaseHandler):
    @gen.coroutine
    def get(self, account_id=None):
        """
        For helping customers with their accounts.
        """
        if not account_id:
            self.write({
                "success": False,
                "msg": "You must specify a account_id via the URL (/UUID/)."
            })

        assumed_role_credentials = None
        try:
            # We then assume the administrator role for the sub-account we created
            assumed_role_credentials = yield self.task_spawner.get_assume_role_credentials(
                str(account_id),
                3600  # One hour - TODO CHANGEME
            )
        except ClientError as boto_error:
            self.logger("Assume role boto error:" + repr(boto_error), "error")
            # If it's not an AccessDenied exception it's not what we except so we re-raise
            if boto_error.response["Error"]["Code"] != "AccessDenied":
                self.logger("Unexpected Boto3 response: " +
                            boto_error.response["Error"]["Code"])
                self.logger(boto_error.response)
                raise boto_error

        if not assumed_role_credentials:
            self.write({
                "success": False,
                "msg": "Unable to get assume role credentials for provided account"
            })
            raise gen.Return()

        self.write({
            "success": True,
            "access_key_id": assumed_role_credentials["access_key_id"],
            "secret_access_key": assumed_role_credentials["secret_access_key"],
            "session_token": assumed_role_credentials["session_token"]
        })


class UpdateIAMConsoleUserIAM(BaseHandler):
    @gen.coroutine
    def get(self):
        """
        This blows away all the IAM policies for all customer AWS accounts
        and updates it with the latest policy.
        """
        self.write({
            "success": True,
            "msg": "Console accounts are being updated!"
        })
        self.finish()

        dbsession = self.db_session_maker()
        aws_accounts = dbsession.query(AWSAccount).filter(
            sql_or(
                AWSAccount.aws_account_status == "IN_USE",
                AWSAccount.aws_account_status == "AVAILABLE",
            )
        ).all()

        aws_account_dicts = []
        for aws_account in aws_accounts:
            aws_account_dicts.append(
                aws_account.to_dict()
            )
        dbsession.close()

        for aws_account_dict in aws_account_dicts:
            self.logger("Updating console account for AWS account ID " +
                        aws_account_dict["account_id"] + "...")
            yield self.task_spawner.recreate_aws_console_account(
                aws_account_dict,
                False
            )

        self.logger("AWS console accounts updated successfully!")


class OnboardThirdPartyAWSAccountPlan(BaseHandler):
    @gen.coroutine
    def get(self):
        """
        Imports a third-party AWS account into the database and sends out
        a terraform plan email with what will happen when it's fully set up.
        """

        # Get AWS account ID
        account_id = self.get_argument(
            "account_id",
            default=None,
            strip=True
        )

        if not account_id:
            self.write({
                "success": False,
                "msg": "Please provide an 'account_id' to onboard this AWS account!"
            })
            raise gen.Return()

        final_email_html = """
        <h1>Terraform Plan Results for Onboarding Third-Party Customer AWS Account</h1>
        Please note that this is <b>not</b> applying these changes.
        It is purely to understand what would happen if we did.
        """

        # First we set up the AWS Account in our database so we have a record
        # of it going forward. This also creates the AWS console user.
        self.logger("Adding third-party AWS account to the database...")
        yield self.task_spawner.create_new_sub_aws_account(
            "THIRDPARTY",
            account_id
        )

        dbsession = self.db_session_maker()
        third_party_aws_account = dbsession.query(AWSAccount).filter_by(
            account_id=account_id,
            account_type="THIRDPARTY"
        ).first()
        third_party_aws_account_dict = third_party_aws_account.to_dict()
        dbsession.close()

        self.logger(
            "Performing a terraform plan against the third-party account...")
        terraform_plan_output = yield self.task_spawner.terraform_plan(
            third_party_aws_account_dict
        )

        # Convert terraform plan terminal output to HTML
        ansiconverter = Ansi2HTMLConverter()
        terraform_output_html = ansiconverter.convert(
            terraform_plan_output
        )

        final_email_html += "<hr /><h1>AWS Account " + \
            third_party_aws_account_dict["account_id"] + "</h1>"
        final_email_html += terraform_output_html

        final_email_html += "<hr /><b>That is all.</b>"

        self.logger("Sending email with results from terraform plan...")
        yield self.task_spawner.send_email(
            self.app_config.get("alerts_email"),

            # Make subject unique so Gmail doesn't group
            "Terraform Plan Results for Onboarding Third-Party AWS Account " + \
            str(int(time.time())),

            # No text version of email
            False,

            final_email_html
        )

        self.write({
            "success": True,
            "msg": "Successfully added AWS account " + account_id + " to database and sent plan email!"
        })


class OnboardThirdPartyAWSAccountApply(BaseHandler):
    @gen.coroutine
    def get(self):
        """
        Finalizes the third-party AWS account onboarding import process.

        This should only be done after the Terraform plan has been reviewed
        and it looks appropriate to be applied.
        """

        # Get AWS account ID
        account_id = self.get_argument(
            "account_id",
            default=None,
            strip=True
        )

        # Get Refinery user ID
        user_id = self.get_argument(
            "user_id",
            default=None,
            strip=True
        )

        if not account_id:
            self.write({
                "success": False,
                "msg": "Please provide an 'account_id' to onboard this AWS account!"
            })
            raise gen.Return()

        if not user_id:
            self.write({
                "success": False,
                "msg": "Please provide an 'user_id' to onboard this AWS account!"
            })
            raise gen.Return()

        dbsession = self.db_session_maker()
        third_party_aws_account = dbsession.query(AWSAccount).filter_by(
            account_id=account_id,
            account_type="THIRDPARTY"
        ).first()
        third_party_aws_account_dict = third_party_aws_account.to_dict()
        dbsession.close()

        self.logger("Creating the '" + THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME +
                    "' role for Lambda executions...")
        yield self.task_spawner.create_third_party_aws_lambda_execute_role(
            third_party_aws_account_dict
        )

        current_aws_account = None

        try:
            self.logger(
                "Creating Refinery base infrastructure on third-party AWS account...")
            account_provisioning_details = yield self.task_spawner.terraform_configure_aws_account(
                third_party_aws_account_dict
            )

            dbsession = self.db_session_maker()

            # Get the AWS account specified
            current_aws_account = dbsession.query(AWSAccount).filter(
                AWSAccount.account_id == account_id,
            ).first()

            # Pull the user from the database
            refinery_user = dbsession.query(User).filter_by(
                id=user_id
            ).first()

            # Grab the previous AWS account specified with the Refinery account
            previous_aws_account = dbsession.query(AWSAccount).filter(
                AWSAccount.organization_id == refinery_user.organization_id
            ).first()

            previous_aws_account_dict = previous_aws_account.to_dict()
            previous_aws_account_id = previous_aws_account.id

            self.logger(
                "Previously-assigned AWS Account has UUID of " + previous_aws_account_id)

            # Set the previously-assigned AWS account to be
            previous_aws_account.aws_account_status = "NEEDS_CLOSING"
            previous_aws_account.organization_id = None

            # Update the AWS account with this new information
            current_aws_account.redis_hostname = account_provisioning_details["redis_hostname"]
            current_aws_account.terraform_state = account_provisioning_details["terraform_state"]
            current_aws_account.ssh_public_key = account_provisioning_details["ssh_public_key"]
            current_aws_account.ssh_private_key = account_provisioning_details["ssh_private_key"]
            current_aws_account.aws_account_status = "IN_USE"
            current_aws_account.organization_id = refinery_user.organization_id

            # Create a new terraform state version
            terraform_state_version = TerraformStateVersion()
            terraform_state_version.terraform_state = account_provisioning_details[
                "terraform_state"]
            current_aws_account.terraform_state_versions.append(
                terraform_state_version
            )
        except Exception as e:
            if current_aws_account is not None:
                self.logger("An error occurred while provision AWS account '" +
                            current_aws_account.account_id + "' with terraform!", "error")
            print_exc()
            self.logger(e)
            self.logger("Marking the account as 'CORRUPT'...")

            # Mark the account as corrupt since the provisioning failed.
            current_aws_account.aws_account_status = "CORRUPT"
            dbsession.add(current_aws_account)
            dbsession.commit()
            dbsession.close()

            self.write({
                "success": False,
                "exception": str(e),
                "msg": "An error occurred while provisioning AWS account."
            })

            raise gen.Return()

        self.logger("AWS account terraform apply has completed.")
        dbsession.add(previous_aws_account)
        dbsession.add(current_aws_account)
        dbsession.commit()
        dbsession.close()

        # Close the previous Refinery-managed AWS account
        self.logger("Closing previously-assigned Refinery AWS account...")
        self.logger(
            "Freezing the account so it costs us less while we do the process of closing it...")
        yield self.task_spawner.freeze_aws_account(
            previous_aws_account_dict
        )

        self.write({
            "success": True,
            "msg": "Successfully added third-party AWS account " + account_id + " to user ID " + user_id + "."
        })


class ClearAllS3BuildPackages(BaseHandler):
    @gen.coroutine
    def get(self):
        """
        Clears out the S3 build packages of all the Refinery users.

        This just forces everyone to do a rebuild the next time they run code with packages.
        """
        self.write({
            "success": True,
            "msg": "Clear build package job kicked off successfully!"
        })
        self.finish()

        dbsession = self.db_session_maker()
        aws_accounts = dbsession.query(AWSAccount).filter(
            sql_or(
                AWSAccount.aws_account_status == "IN_USE",
                AWSAccount.aws_account_status == "AVAILABLE",
            )
        ).all()

        aws_account_dicts = []
        for aws_account in aws_accounts:
            aws_account_dicts.append(
                aws_account.to_dict()
            )
        dbsession.close()

        for aws_account_dict in aws_account_dicts:
            self.logger("Clearing build packages for account ID " +
                        aws_account_dict["account_id"] + "...")
            yield clear_sub_account_packages(
                self.task_spawner,
                aws_account_dict
            )

        self.logger("S3 package clearing complete.")


class MaintainAWSAccountReserves(BaseHandler):
    @gen.coroutine
    def get(self):
        """
        This job checks the number of AWS accounts in the reserve pool and will
        automatically create accounts for the pool if there are less than the
        target amount. This job is run regularly (every minute) to ensure that
        we always have enough AWS accounts ready to use.
        """
        self.write({
            "success": True,
            "msg": "AWS account maintenance job has been kicked off!"
        })
        self.finish()

        self.terraform_service.maintain_aws_account_reserves()


class PerformTerraformUpdateOnFleet(BaseHandler):
    @gen.coroutine
    def get(self):
        self.write({
            "success": True,
            "msg": "Terraform apply job started, did you plan first?"
        })
        self.finish()
        results = self.terraform_service.terraform_update_fleet()
        all_success = all([r['success'] for i, r in results])

        email_html_tokens = [(
            "<h1>Terraform Apply Results Across the Customer Fleet</h1>"
            "If the subject line doesn't read <b>APPLY SUCCEEDED</b> "
            "you have some work to do!"
        )]

        for account_id, apply_result in results:
            # Convert terraform plan terminal output to HTML
            ansiconverter = Ansi2HTMLConverter()
            success = apply_result['success']
            stdout = apply_result['stdout']
            stderr = apply_result['stderr']
            body = ansiconverter.convert(stdout if success else stderr)

            email_html_tokens.append(
                f"<hr /><h1>AWS Account {account_id}</h1>{body}"
            )

        email_html_tokens.append("<hr /><b>That is all.</b>")

        # Make subject unique so Gmail doesn't group
        timestamp = str(int(time.time()))
        status = "SUCCEEDED" if all_success else "FAILED"
        subject = (
            f"[ APPLY {status} ] "
            f"Terraform Apply Results from Across the Fleet {timestamp}"
        )

        self.logger("Sending email with results from 'terraform apply'...")
        yield self.task_spawner.send_email(
            self.app_config.get("alerts_email"),
            subject,
            False,  # No text version of email
            "".join(email_html_tokens)
        )


class PerformTerraformPlanForAccount(BaseHandler):
    @gen.coroutine
    def get(self, account_id=None):
        """
        This endpoint will perform a Terraform Plan and return the results
        synchronously.
        """

        if not account_id:
            self.write({
                "success": False,
                "msg": "Please provide an 'account_id' to terraform plan for"
            })
            raise gen.Return()

        template = """
        <html>
        <body>
            <h1>Terraform Plan Result for Account: {}</h1>
            Please note that this is <b>not</b> applying these changes.
            It is purely to understand what would happen if we did.
            <hr />
            <h3>Output</h3>
            <p>{}</p>
        </body>
        </html>
        """

        # Convert terraform plan terminal output to HTML
        result = self.terraform_service.terraform_plan_by_account_id(
            account_id)
        ansiconverter = Ansi2HTMLConverter()
        terraform_output_html = ansiconverter.convert(result)
        rendered = template.format(account_id, terraform_output_html)

        self.logger(f"Generated response output for plan: {rendered}")
        self.write(rendered)


class PerformTerraformUpdateForAccount(BaseHandler):
    @gen.coroutine
    def get(self, account_id=None):
        if not account_id:
            self.write({
                "success": False,
                "msg": "Please provide an 'account_id' to terraform apply for"
            })
            raise gen.Return()

        try:
            result = self.terraform_service.terraform_update(account_id)
        except TerraformError as e:
            self.write({
                "success": False,
                "msg": e.args[0]
            })
            raise gen.Return()

        template = """
            <html>
                <body>
                    <h1>Terraform Apply Results for Account {}</h1>
                    <h2>Result: [ APPLY {} ]</h2>
                    <p>{}</p>
                </body>
            </html>
        """

        ansiconverter = Ansi2HTMLConverter()
        success = result['success']
        stdout = result['stdout']
        stderr = result['stderr']
        body = ansiconverter.convert(stdout if success else stderr)
        status = "SUCCEEDED" if success else "FAILED"
        rendered = template.format(account_id, status, body)

        self.logger(f"Results from account 'terraform apply': {rendered}")

        self.write(rendered)


class PerformTerraformPlanOnFleet(BaseHandler):
    @gen.coroutine
    def get(self):
        self.write({
            "success": True,
            "msg": "Terraform plan job has been kicked off!"
        })
        self.finish()

        email_html_tokens = [(
            '<h1>Terraform Plan Results Across the Customer Fleet</h1>'
            'Please note that this is <b>not</b> applying these changes.'
            'It is purely to understand what would happen if we did.'
        )]

        results = self.terraform_service.terraform_plan_on_fleet()

        for aws_account_id, terraform_plan_output in results:
            # Convert terraform plan terminal output to HTML
            ansiconverter = Ansi2HTMLConverter()
            terraform_output_html = ansiconverter.convert(
                terraform_plan_output
            )
            email_html_tokens.extend([
                f"<hr /><h1>AWS Account {aws_account_id}</h1>",
                terraform_output_html
            ])

        email_html_tokens.append("<hr /><b>That is all.</b>")

        self.logger("Sending email with results from terraform plan...")

        timestamp = str(int(time.time()))
        subject = f'Terraform Plan Results from Across the Fleet {timestamp}'

        yield self.task_spawner.send_email(
            self.app_config.get("alerts_email"),
            subject,
            False,  # No text version of email
            "".join(email_html_tokens)
        )


class RunBillingWatchdogJob(BaseHandler):
    @gen.coroutine
    def get(self):
        """
        This job checks the running account totals of each AWS account to see
        if their usage has gone over the safety limits. This is mainly for free
        trial users and for alerting users that they may incur a large bill.
        """
        self.write({
            "success": True,
            "msg": "Watchdog job has been started!"
        })
        self.finish()
        self.logger(
            "[ STATUS ] Initiating billing watchdog job, scanning all accounts to check for billing anomalies...")
        aws_account_running_cost_list = yield self.task_spawner.pull_current_month_running_account_totals()
        self.logger("[ STATUS ] " + str(len(aws_account_running_cost_list)) +
                    " account(s) pulled from billing, checking against rules...")
        yield self.task_spawner.enforce_account_limits(aws_account_running_cost_list)


class RunMonthlyStripeBillingJob(BaseHandler):
    @gen.coroutine
    def get(self):
        """
        Runs at the first of the month and creates auto-finalizing draft
        invoices for all Refinery customers. After it does this it emails
        the "billing_alert_email" email with a notice to review the drafts
        before they auto-finalize after one-hour.
        """
        self.write({
            "success": True,
            "msg": "The billing job has been started!"
        })
        self.finish()
        self.logger(
            "[ STATUS ] Running monthly Stripe billing job to invoice all Refinery customers.")
        date_info = get_last_month_start_and_end_date_strings()

        self.logger("[ STATUS ] Generating invoices for " +
                    date_info["month_start_date"] + " -> " + date_info["next_month_first_day"])

        yield self.task_spawner.generate_managed_accounts_invoices(
            date_info["month_start_date"],
            date_info["next_month_first_day"],
        )
        self.logger("[ STATUS ] Stripe billing job has completed!")


class CleanupDanglingResourcesDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(
        self,
        lambda_manager,
        api_gateway_manager,
        schedule_trigger_manager,
        sns_manager,
        sqs_manager,
        aws_resource_enumerator
    ):
        pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class CleanupDanglingResources(BaseHandler):
    dependencies = CleanupDanglingResourcesDependencies
    lambda_manager = None
    api_gateway_manager = None
    schedule_trigger_manager = None
    sns_manager = None
    sqs_manager = None
    aws_resource_enumerator = None

    @gen.coroutine
    def get(self, user_id=None):
        delete_resources = self.get_argument("confirm", False)

        # Get user's organization
        user = self.dbsession.query(User).filter_by(
            id=user_id
        ).first()

        if not user:
            self.write({
                "success": False,
                "msg": "No user was found with that UUID."
            })
            raise gen.Return()

        aws_account = self.dbsession.query(AWSAccount).filter_by(
            organization_id=user.organization_id,
            aws_account_status="IN_USE"
        ).first()

        if not aws_account:
            self.write({
                "success": False,
                "msg": "No AWS account found for user."
            })
            raise gen.Return()

        # Get credentials to perform scan
        credentials = aws_account.to_dict()

        # Get user dangling records
        dangling_resources = yield get_user_dangling_resources(
            self.aws_resource_enumerator,
            self.db_session_maker,
            user_id,
            credentials
        )

        number_of_resources = len(dangling_resources)

        self.logger(str(len(dangling_resources)) +
                    " resource(s) enumerated in account.")

        # If the "confirm" parameter is passed we can proceed to delete it all.
        if delete_resources:
            self.logger("Deleting all dangling resources...")

            # Tear down all dangling nodes
            teardown_results = yield teardown_infrastructure(
                self.api_gateway_manager,
                self.lambda_manager,
                self.schedule_trigger_manager,
                self.sns_manager,
                self.sqs_manager,
                credentials,
                dangling_resources
            )

            self.logger(teardown_results)

            self.logger("Deleted all dangling resources successfully!")

        self.write({
            "success": True,
            "total_resources": len(dangling_resources),
            "result": dangling_resources
        })


class ClearStripeInvoiceDraftsDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, billing_spawner):
        pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class ClearStripeInvoiceDrafts(BaseHandler):
    dependencies = ClearStripeInvoiceDraftsDependencies
    billing_spawner = None

    @gen.coroutine
    def get(self):
        self.logger("Clearing all draft Stripe invoices...")
        yield self.billing_spawner.clear_draft_invoices()

        self.write({
            "success": True,
            "msg": "Invoice drafts have been cleared!"
        })


class ResetIAMConsoleUserIAMForAccount(BaseHandler):
    @gen.coroutine
    def get(self, account_id=None):
        """
        This blows away all the IAM policies for a specific AWS account and updates it with the latest policy.
        """

        # Get AWS account ID
        account_id = self.get_argument(
            "account_id",
            default=None,
            strip=True
        )

        if not account_id:
            self.write({
                "success": False,
                "msg": "Please provide an 'account_id' to reset the IAM Console user"
            })
            raise gen.Return()

        dbsession = self.db_session_maker()
        aws_account_result = dbsession.query(AWSAccount).filter(
            AWSAccount.account_id == account_id
        ).filter(
            sql_or(
                AWSAccount.aws_account_status == "IN_USE",
                AWSAccount.aws_account_status == "AVAILABLE",
            )
        ).first()

        if aws_account_result is None:
            msg = "Could not find account to reset IAM for: " + account_id
            self.logger(msg, "error")
            self.write({
                "success": False,
                "msg": msg
            })
            raise gen.Return()

        aws_account_dict = aws_account_result.to_dict()

        dbsession.close()

        self.logger("Updating console account for single AWS account ID " +
                    aws_account_dict["account_id"] + "...")
        yield self.task_spawner.recreate_aws_console_account(
            aws_account_dict,
            False,
            # We set this flag so that if the user was deleted, it will be recreated
            force_continue=True
        )

        self.logger(
            "AWS console account updated successfully for account: " + account_id)

        self.write({
            "success": True,
            "msg": "Console user successfully updated for: " + account_id
        })
        self.finish()


class MarkAccountNeedsClosing(BaseHandler):
    @gen.coroutine
    def post(self):
        """
        Mark an account as "NEEDS_CLOSING" so that it can be
        cleaned up when aws accounts are being reaped.
        """
        schema = {
            "type": "object",
            "properties": {
                    "email": {
                        "type": "string",
                        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    }
            },
            "required": [
                "email"
            ]
        }

        validate_schema(self.json, schema)

        ok = yield self.task_spawner.mark_account_needs_closing(self.json['email'])

        self.write({
            "ok": ok,
        })


class RemoveNeedsClosingAccounts(BaseHandler):
    @gen.coroutine
    def get(self):
        """
        Removes accounts which have been marked as 'NEEDS_CLOSING'
        """
        removed_count = yield self.task_spawner.do_account_cleanup()

        self.write({
            "removed": removed_count,
        })
