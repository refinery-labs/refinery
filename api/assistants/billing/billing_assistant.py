import stripe

from tornado.concurrent import run_on_executor

from assistants.aws_account_management.account_usage_manager import get_sub_account_billing_data
from tasks.aws_account import mark_account_needs_closing
from utils.base_spawner import BaseSpawner
from utils.performance_decorators import emit_runtime_metrics

from assistants.accounts import get_user_free_trial_information
from json import loads
from models import AWSAccount, Organization
from tasks.email import send_email, send_account_freeze_email
from utils.general import logit


def generate_managed_accounts_invoices(aws_client_factory, aws_cost_explorer, app_config, db_session_maker, start_date_string, end_date_string):
    """
    Bills ultimately belong to the organization but are paid by
    the ADMINS of the organization. So we generate the invoices and
    then send them to the admins on the account for payment.

    Note that this is purely for accounts which are "managed" meaning
    we own the billing of the sub-AWS accounts and we upcharge and
    bill the customer.
    """
    # Pull a list of organizations to generate invoices for
    dbsession = db_session_maker()
    organizations = dbsession.query(Organization)

    organization_ids = []

    for organization in organizations:
        organization_dict = organization.to_dict()
        organization_ids.append(
            organization_dict["id"]
        )

    dbsession.close()

    # List of invoices to send out at the end
    """
    {
        # To send invoice emails
        "admin_stripe_id": "...",
        "aws_account_bills": [],
    }
    """
    invoice_list = []

    # Setting for if Refinery should just finalize the invoices
    # or if manual approve/editing is enabled. One is more careful
    # than the others.
    finalize_invoices_enabled = loads(
        app_config.get("stripe_finalize_invoices")
    )

    # Iterate over each organization
    for organization_id in organization_ids:
        dbsession = db_session_maker()
        organization = dbsession.query(Organization).filter_by(
            id=organization_id
        ).first()

        organization_dict = organization.to_dict()

        # If the organization is disabled we just skip it
        if organization.disabled == True:
            continue

        # If the organization is billing exempt, we skip it
        if organization.billing_exempt == True:
            continue

        # Check if the organization billing admin has validated
        # their email address. If not it means they never finished
        # the signup process so we can skip them.
        if organization.billing_admin_user.email_verified == False:
            continue

        current_organization_invoice_data = {
            "admin_stripe_id": "...",
            "aws_account_bills": [],
        }

        # Pull the organization billing admin and send them
        # the invoice email so they can pay it.
        current_organization_invoice_data["admin_stripe_id"] = organization.billing_admin_user.payment_id

        # Get AWS accounts from organization
        organization_aws_accounts = []
        for aws_account in organization.aws_accounts:
            organization_aws_accounts.append(
                aws_account.to_dict()
            )
        dbsession.close()

        # Pull billing information for each AWS account
        for aws_account_dict in organization_aws_accounts:
            billing_information = get_sub_account_billing_data(
                app_config,
                db_session_maker,
                aws_cost_explorer,
                aws_client_factory,
                aws_account_dict["account_id"],
                aws_account_dict["account_type"],
                start_date_string,
                end_date_string,
                "monthly",
                False
            )

            current_organization_invoice_data["aws_account_bills"].append({
                "aws_account_label": aws_account_dict["account_label"],
                "aws_account_id": aws_account_dict["account_id"],
                "billing_information": billing_information,
            })

        if "admin_stripe_id" in current_organization_invoice_data and current_organization_invoice_data["admin_stripe_id"]:
            invoice_list.append(
                current_organization_invoice_data
            )

    for invoice_data in invoice_list:
        for aws_account_billing_data in invoice_data["aws_account_bills"]:
            # We send one bill per managed AWS account if they have multiple

            for service_cost_data in aws_account_billing_data["billing_information"]["service_breakdown"]:
                line_item_cents = int(
                    float(service_cost_data["total"]) * 100
                )

                # If the item costs zero cents don't add it to the bill.
                if line_item_cents > 0:
                    # Don't add "Managed" to the base-service fee.
                    if "Fee" in service_cost_data["service_name"]:
                        service_description = service_cost_data["service_name"]
                    else:
                        service_description = "Managed " + \
                                              service_cost_data["service_name"]

                    if aws_account_billing_data["aws_account_label"].strip() != "":
                        service_description = service_description + \
                                              " (Cloud Account: '" + \
                                              aws_account_billing_data["aws_account_label"] + "')"

                    # noinspection PyUnresolvedReferences
                    stripe.InvoiceItem.create(
                        # Stripe bills in cents!
                        amount=line_item_cents,
                        currency=str(service_cost_data["unit"]).lower(),
                        customer=invoice_data["admin_stripe_id"],
                        description=service_description,
                    )

            invoice_creation_params = {
                "customer": invoice_data["admin_stripe_id"],
                "auto_advance": True,
                "billing": "charge_automatically",
                "metadata": {
                    "aws_account_id": aws_account_billing_data["aws_account_id"]
                }
            }

            try:
                # noinspection PyUnresolvedReferences
                customer_invoice = stripe.Invoice.create(
                    **invoice_creation_params
                )

                if finalize_invoices_enabled:
                    customer_invoice.send_invoice()
            except Exception as e:
                logit(
                    "Exception occurred while creating customer invoice, parameters were the following: ")
                logit(invoice_creation_params)
                logit(e)

    # Notify finance department that they have an hour to review the invoices
    return send_email(
        app_config,
        app_config.get("billing_alert_email"),
        "[URGENT][IMPORTANT]: Monthly customer invoice generation has completed. One hour to auto-finalization.",
        False,
        "The monthly Stripe invoice generation has completed. You have <b>one hour</b> to review invoices before they go out to customers.<br /><a href=\"https://dashboard.stripe.com/invoices\"><b>Click here to review the generated invoices</b></a><br /><br />",
    )


def enforce_account_limits(app_config, aws_client_factory, db_session_maker, aws_account_freezer, aws_account_running_cost_list):
    """
    {
            "aws_account_id": "00000000000",
            "billing_total": "12.39",
            "unit": "USD",
    }
    """
    dbsession = db_session_maker()

    # Pull the configured free trial account limits
    free_trial_user_max_amount = float(
        app_config.get("free_trial_billing_limit")
    )

    # Iterate over the input list and pull the related accounts
    for aws_account_info in aws_account_running_cost_list:
        # Pull relevant AWS account
        aws_account = dbsession.query(AWSAccount).filter_by(
            account_id=aws_account_info["aws_account_id"],
            aws_account_status="IN_USE",
        ).first()

        # If there's no related AWS account in the database
        # we just skip over it because it's likely a non-customer
        # AWS account
        if aws_account is None:
            continue

        # Pull related organization
        owner_organization = dbsession.query(Organization).filter_by(
            id=aws_account.organization_id
        ).first()

        # Check if the user is a free trial user
        user_trial_info = get_user_free_trial_information(
            owner_organization.billing_admin_user
        )

        # If they are a free trial user, check if their usage has
        # exceeded the allowed limits
        exceeds_free_trial_limit = float(
            aws_account_info["billing_total"]) >= free_trial_user_max_amount
        if user_trial_info["is_using_trial"] and exceeds_free_trial_limit:
            logit("[ STATUS ] Enumerated user has exceeded their free trial.")
            logit("[ STATUS ] Taking action against free-trial account...")
            freeze_result = aws_account_freezer.freeze_aws_account(
                app_config,
                aws_client_factory,
                db_session_maker,
                aws_account.to_dict()
            )

            # Send account frozen email to us to know that it happened
            send_account_freeze_email(
                app_config,
                aws_account_info["aws_account_id"],
                aws_account_info["billing_total"],
                owner_organization.billing_admin_user.email
            )

    dbsession.close()


class BillingSpawner(BaseSpawner):

    def __init__(
            self,
            aws_cloudwatch_client,
            logger,
            app_config,
            db_session_maker,
            aws_client_factory,
            aws_account_freezer
    ):
        super().__init__(aws_cloudwatch_client, logger, app_config)

        self.db_session_maker = db_session_maker
        self.aws_client_factory = aws_client_factory
        self.aws_account_freezer = aws_account_freezer

    @run_on_executor
    @emit_runtime_metrics("clear_draft_invoices")
    def clear_draft_invoices(self):
        """
        Clears all Stripe invoices which are in a "draft" state. Useful for backing out of
        a state where invalid invoices were generated and you need to clear everything out
        and then try again.
        """
        invoice_ids_to_delete = []

        for stripe_invoice in stripe.Invoice.list():
            if stripe_invoice["status"] == "draft":
                invoice_ids_to_delete.append(
                    stripe_invoice["id"]
                )

        for invoice_id in invoice_ids_to_delete:
            logit("Deleting invoice ID '" + invoice_id + "'...")
            response = stripe.Invoice.delete(
                invoice_id,
            )

        logit("Deleting draft invoices completed successfully!")

    @run_on_executor
    def get_account_cards(self, stripe_customer_id):
        return BillingSpawner._get_account_cards(stripe_customer_id)

    @staticmethod
    def _get_account_cards(stripe_customer_id):
        # Pull all of the metadata for the cards the customer
        # has on file with Stripe
        cards = stripe.Customer.list_sources(
            stripe_customer_id,
            object="card",
            limit=100,
        )

        # Pull the user's default card and add that
        # metadata to the card
        customer_info = BillingSpawner._get_stripe_customer_information(
            stripe_customer_id
        )

        for card in cards:
            is_primary = False
            if card["id"] == customer_info["default_source"]:
                is_primary = True
            card["is_primary"] = is_primary

        return cards["data"]

    @run_on_executor
    def get_stripe_customer_information(self, stripe_customer_id):
        return BillingSpawner._get_stripe_customer_information(stripe_customer_id)

    @staticmethod
    def _get_stripe_customer_information(stripe_customer_id):
        return stripe.Customer.retrieve(
            stripe_customer_id
        )

    @run_on_executor
    @emit_runtime_metrics("enforce_account_limits")
    def enforce_account_limits(self, aws_account_running_cost_list):
        return enforce_account_limits(
            self.app_config,
            self.aws_client_factory,
            self.db_session_maker,
            self.aws_account_freezer,
            aws_account_running_cost_list
        )

    @run_on_executor
    @emit_runtime_metrics("mark_account_needs_closing")
    def mark_account_needs_closing(self, email):
        return mark_account_needs_closing(self.db_session_maker, email)
