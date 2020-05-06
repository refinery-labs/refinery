from jsonschema import validate as validate_schema
from tornado import gen

from assistants.task_spawner.actions import get_current_month_start_and_end_date_strings
from controller import BaseHandler
from controller.billing.schemas import *
from controller.decorators import authenticated
from pyexceptions.billing import CardIsPrimaryException


class GetBillingMonthTotals(BaseHandler):
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

        billing_data = yield self.task_spawner.get_sub_account_month_billing_data(
            credentials["account_id"],
            credentials["account_type"],
            self.json["billing_month"],
            True
        )

        self.write({
            "success": True,
            "billing_data": billing_data,
        })


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


# UNUSED
class GetBillingDateRangeForecast(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Pulls the billing totals for a given date range.

        This allows for the frontend to pull things like:
        * The user's current total costs for the month
        * The total costs for the last three months.
        """
        current_user = self.get_authenticated_user()
        credentials = self.get_authenticated_user_cloud_configuration()

        date_info = get_current_month_start_and_end_date_strings()

        forecast_data = yield self.task_spawner.get_sub_account_billing_forecast(
            credentials["account_id"],
            date_info["current_date"],
            date_info["next_month_first_day"],
            "monthly"
        )

        self.write(forecast_data)
