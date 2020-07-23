import pinject
from jsonschema import validate as validate_schema
from tornado import gen

from assistants.aws_account_management.account_usage_manager import get_current_month_start_and_end_date_strings, \
    get_last_month_start_and_end_date_strings, AwsAccountUsageManager
from assistants.billing.billing_assistant import BillingSpawner
from controller import BaseHandler
from controller.billing.schemas import *
from controller.decorators import authenticated
from pyexceptions.billing import CardIsPrimaryException


class GetBillingTotalsDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, aws_account_usage_manager):
        pass


class GetBillingMonthTotals(BaseHandler):
    dependencies = GetBillingTotalsDependencies
    aws_account_usage_manager: AwsAccountUsageManager = None

    @authenticated
    @gen.coroutine
    def post(self):
        """
        Pulls the billing totals for a given date range.

        This allows for the frontend to pull things like:
        * The user's current total costs for the month
        * The total costs for the last three months.
        """
        validate_schema(self.json, GET_BILLING_MONTH_TOTALS_SCHEMA)

        credentials = self.get_authenticated_user_cloud_configuration()

        billing_data = yield self.aws_account_usage_manager.get_sub_account_month_billing_data(
            credentials["account_id"],
            credentials["account_type"],
            self.json["billing_month"],
            True
        )

        self.write({
            "success": True,
            "billing_data": billing_data,
        })


class GetBillingDateRangeForecast(BaseHandler):
    dependencies = GetBillingTotalsDependencies
    aws_account_usage_manager: AwsAccountUsageManager = None

    @authenticated
    @gen.coroutine
    def post(self):
        """
        Pulls the billing totals for a given date range.

        This allows for the frontend to pull things like:
        * The user's current total costs for the month
        * The total costs for the last three months.
        """
        credentials = self.get_authenticated_user_cloud_configuration()

        date_info = get_current_month_start_and_end_date_strings()

        forecast_data = yield self.aws_account_usage_manager.get_sub_account_billing_forecast(
            credentials["account_id"],
            date_info["current_date"],
            date_info["next_month_first_day"],
            "monthly"
        )

        self.write(forecast_data)


class AddCreditCardToken(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Adds a credit card token to a given user's Stripe record.

        THIS DOES NOT STORE CREDIT CARD INFORMATION, DO NOT EVER PASS
        CREDIT CARD INFORMATION TO IT. DON'T EVEN *THINK* ABOUT DOING
        IT OR I WILL PERSONALLY SLAP YOU. -mandatory
        """
        validate_schema(self.json, ADD_CREDIT_CARD_TOKEN_SCHEMA)

        current_user = self.get_authenticated_user()

        yield self.task_spawner.associate_card_token_with_customer_account(
            current_user.payment_id,
            self.json["token"]
        )

        self.write({
            "success": True,
            "msg": "The credit card has been successfully added to your account!"
        })


class ListCreditCards(BaseHandler):
    @authenticated
    @gen.coroutine
    def get(self):
        """
        List the credit cards the user has on file, returns
        just the non-PII info that we get back from Stripe
        """
        current_user = self.get_authenticated_user()

        cards_info_list = yield self.task_spawner.get_account_cards(
            current_user.payment_id,
        )

        # Filter card info
        filtered_card_info_list = []

        # The keys we're fine with passing from back Stripe
        returnable_keys = [
            "id",
            "brand",
            "country",
            "exp_month",
            "exp_year",
            "last4",
            "is_primary"
        ]

        for card_info in cards_info_list:
            filtered_card_info = {}
            for key, value in card_info.items():
                if key in returnable_keys:
                    filtered_card_info[key] = value

            filtered_card_info_list.append(
                filtered_card_info
            )

        self.write({
            "success": True,
            "cards": filtered_card_info_list
        })


class DeleteCreditCard(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Deletes a credit card from the user's Stripe account.

        This is not allowed if the payment method is the only
        one on file for that account.
        """
        validate_schema(self.json, DELETE_CREDIT_CARD_SCHEMA)

        current_user = self.get_authenticated_user()

        try:
            yield self.task_spawner.delete_card_from_account(
                current_user.payment_id,
                self.json["id"]
            )
        except CardIsPrimaryException:
            self.error(
                "You cannot delete your primary payment method, you must have at least one available to pay your bills.",
                "CANT_DELETE_PRIMARY"
            )
            raise gen.Return()

        self.write({
            "success": True,
            "msg": "The card has been successfully been deleted from your account!"
        })


class MakeCreditCardPrimary(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Sets a given card to be the user's primary credit card.
        """
        validate_schema(self.json, MAKE_CREDIT_CARD_PRIMARY_SCHEMA)

        current_user = self.get_authenticated_user()

        try:
            yield self.task_spawner.set_stripe_customer_default_payment_source(
                current_user.payment_id,
                self.json["id"]
            )
        except Exception as e:
            self.logger(
                "exception while making card primary: id({}) {}".format(self.json["id"], str(e)), "error"
            )
            self.error(
                "An error occurred while making the card your primary.",
                "GENERIC_MAKE_PRIMARY_ERROR"
            )

        self.write({
            "success": True,
            "msg": "You have set this card to be your primary succesfully."
        })


class RunBillingWatchdogJobDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, aws_account_usage_manager, billing_spawner):
        pass


class RunBillingWatchdogJob(BaseHandler):
    dependencies = RunBillingWatchdogJobDependencies
    aws_account_usage_manager: AwsAccountUsageManager = None
    billing_spawner: BillingSpawner = None

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

        self.logger("[ STATUS ] Initiating billing watchdog job, scanning all accounts to check for billing anomalies...")

        aws_account_running_cost_list = yield self.aws_account_usage_manager.pull_current_month_running_account_totals()

        self.logger("[ STATUS ] " + str(len(aws_account_running_cost_list)) + " account(s) pulled from billing, checking against rules...")

        yield self.billing_spawner.enforce_account_limits(aws_account_running_cost_list)


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
        self.logger("[ STATUS ] Running monthly Stripe billing job to invoice all Refinery customers.")
        date_info = get_last_month_start_and_end_date_strings()

        self.logger("[ STATUS ] Generating invoices for " + date_info["month_start_date"] + " -> " + date_info["next_month_first_day"])

        yield self.task_spawner.generate_managed_accounts_invoices(
            date_info["month_start_date"],
            date_info["next_month_first_day"],
        )
        self.logger("[ STATUS ] Stripe billing job has completed!")


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
