import stripe


from assistants.accounts import get_user_free_trial_information
from assistants.task_spawner.actions import get_current_month_start_and_end_date_strings
from assistants.task_spawner.actions import is_organization_first_month
from assistants.task_spawner.actions import get_billing_rounded_float
from assistants.task_spawner.actions import get_deployed_projects_count
from assistants.task_spawner.actions import get_active_deployed_projects_count
from botocore.exceptions import ClientError
from datetime import timedelta, datetime
from json import loads
from models import AWSAccount, Organization, CachedBillingCollection, CachedBillingItem
from numpy import format_float_positional
from pystache import render
from tasks.aws_account import freeze_aws_account
from tasks.email import send_email, send_account_freeze_email
from time import time
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


def pull_current_month_running_account_totals(aws_cost_explorer):
    """
    This runs through all of the sub-AWS accounts managed
    by Refinery and returns an array like the following:
    {
            "aws_account_id": "00000000000",
            "billing_total": "12.39",
            "unit": "USD",
    }
    """
    date_info = get_current_month_start_and_end_date_strings()

    metric_name = "NetUnblendedCost"
    aws_account_running_cost_list = []

    ce_params = {
        "TimePeriod": {
            "Start": date_info["month_start_date"],
            "End": date_info["next_month_first_day"],
        },
        "Granularity": "MONTHLY",
        "Metrics": [
            metric_name
        ],
        "GroupBy": [
            {
                "Type": "DIMENSION",
                "Key": "LINKED_ACCOUNT"
            }
        ]
    }

    ce_response = {}

    # Bound this loop to only execute MAX_LOOP_ITERATION times
    for _ in range(1000):
        ce_response = aws_cost_explorer.get_cost_and_usage(
            **ce_params
        )
        account_billing_results = ce_response["ResultsByTime"][0]["Groups"]

        for account_billing_result in account_billing_results:
            aws_account_running_cost_list.append({
                "aws_account_id": account_billing_result["Keys"][0],
                "billing_total": account_billing_result["Metrics"][metric_name]["Amount"],
                "unit": account_billing_result["Metrics"][metric_name]["Unit"],
            })

        # Stop here if there are no more pages to iterate through.
        if ("NextPageToken" in ce_response) == False:
            break

        # If we have a next page token, then add it to our
        # parameters for the next paginated calls.
        ce_params["NextPageToken"] = ce_response["NextPageToken"]

    return aws_account_running_cost_list


def enforce_account_limits(app_config, aws_client_factory, db_session_maker, aws_account_running_cost_list):
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
            freeze_result = freeze_aws_account(
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


def get_sub_account_month_billing_data(app_config, db_session_maker, aws_cost_explorer, aws_client_factory,
                                       account_id, account_type, billing_month, use_cache):
    # Parse the billing month into a datetime object
    billing_month_datetime = datetime.strptime(
        billing_month,
        "%Y-%m"
    )

    # Get first day of the month
    billing_start_date = billing_month_datetime.strftime("%Y-%m-%d")

    # Get the first day of the next month
    # This is some magic to ensure we end up on the next month since a month
    # never has 32 days.
    next_month_date = billing_month_datetime + timedelta(days=32)
    billing_end_date = next_month_date.strftime("%Y-%m-01")

    return get_sub_account_billing_data(
        app_config,
        db_session_maker,
        aws_cost_explorer,
        aws_client_factory,
        account_id,
        account_type,
        billing_start_date,
        billing_end_date,
        "monthly",
        use_cache
    )


def get_sub_account_billing_data(app_config, db_session_maker, aws_cost_explorer, aws_client_factory,
                                 account_id, account_type, org_id, start_date, end_date, granularity, use_cache):
    """
    Pull the service breakdown list and return it along with the totals.
    Note that this data is not marked up. This function does the work of marking it up.
    {
            "bill_total": {
                    "total": "283.92",
                    "unit": "USD"
            },
            "service_breakdown": [
                    {
                            "service_name": "AWS Cost Explorer",
                            "total": "1.14",
                            "unit": "USD"
                    },
            ...
    """
    service_breakdown_list = get_sub_account_service_breakdown_list(
        app_config,
        db_session_maker,
        aws_cost_explorer,
        aws_client_factory,
        account_id,
        account_type,
        start_date,
        end_date,
        granularity,
        use_cache
    )

    return_data = {
        "bill_total": {
            "total": 0,
            "unit": "USD",
        },
        "service_breakdown": []
    }

    total_amount = 0.00

    # Remove some of the AWS branding from the billing
    remove_aws_branding_words = [
        "AWS",
        "Amazon",
    ]

    # Keywords which remove the item from the billing line
    not_billed_words = [
        "Elastic Compute Cloud",
        "EC2"
    ]

    markup_multiplier = 1 + (int(app_config.get("mark_up_percent")) / 100)

    # Markup multiplier
    if account_type == "THIRDPARTY":
        # For the self-hosted (THIRDPARTY) accounts the multiplier is just 1
        # this is because we normally double the AWS pricing and pay half to AWS.
        # In the THIRDPARTY situation, the customer pays AWS directly and we just
        # take our cut off the top.
        markup_multiplier = 1

    # Check if this is the first billing month
    is_first_account_billing_month = is_organization_first_month(
        db_session_maker,
        account_id
    )

    for service_breakdown_info in service_breakdown_list:
        # Remove branding words from service name
        service_name = service_breakdown_info["service_name"]
        for aws_branding_word in remove_aws_branding_words:
            service_name = service_name.replace(
                aws_branding_word,
                ""
            ).strip()

        # If it's an AWS EC2-related billing item we strike it
        # because it's part of our $5 base fee
        should_be_ignored = False
        for not_billed_word in not_billed_words:
            if not_billed_word in service_name:
                should_be_ignored = True

        # If it matches our keywords we'll strike it from
        # the bill
        if should_be_ignored:
            continue

        # Mark up the total for the service
        service_total = float(service_breakdown_info["total"])

        # Don't add it as a line item if it's zero
        if service_total > 0:
            service_total = get_billing_rounded_float(
                service_total
            ) * markup_multiplier

            return_data["service_breakdown"].append({
                "service_name": service_name,
                "unit": service_breakdown_info["unit"],
                "total": ("%.2f" % service_total),
            })

            total_amount = total_amount + service_total

    # Get number of deployed projects
    deployed_project_count = get_deployed_projects_count(
        db_session_maker,
        org_id,
        start_date,
        end_date
    )

    active_deployed_project_count = get_active_deployed_projects_count(
        db_session_maker,
        org_id
    )

    # This is where we upgrade the billing total if it's not at least $5/mo
    # $5/mo is our floor price. If there are no deployed projects then the
    # billing total is reduced to $0.
    if total_amount < 5.00 and is_first_account_billing_month == False:
        if deployed_project_count + active_deployed_project_count == 0:
            amount_to_add = (5.00 - total_amount)
            return_data["service_breakdown"].append({
                "service_name": "Floor Fee (Bills are minimum $5/month, see refinery.io/pricing for more information).",
                "unit": "usd",
                "total": ("%.2f" % amount_to_add),
            })
            total_amount = 5.00

    return_data["bill_total"] = ("%.2f" % total_amount)

    return return_data


def get_sub_account_service_breakdown_list(app_config, db_session_maker, aws_cost_explorer, aws_client_factory,
                                           account_id, account_type, start_date, end_date, granularity, use_cache):
    """
    Return format:

    [
            {
                    "service_name": "EC2 - Other",
                    "unit": "USD",
                    "total": "10.0245523",
            }
            ...
    ]
    """
    dbsession = db_session_maker()
    # Pull related AWS account and get the database ID for it
    aws_account = dbsession.query(AWSAccount).filter_by(
        account_id=account_id,
    ).first()

    # If the use_cache is enabled we'll check the database for an
    # already cached bill.
    # The oldest a cached bill can be is 24 hours, otherwise a new
    # one will be generated and cached. This allows our customers to
    # always have a daily service total if they want it.
    if use_cache:
        current_timestamp = int(time())
        # Basically 24 hours before the current time.
        oldest_usable_cached_result_timestamp = current_timestamp - \
            (60 * 60 * 24)
        billing_collection = dbsession.query(CachedBillingCollection).filter_by(
            billing_start_date=start_date,
            billing_end_date=end_date,
            billing_granularity=granularity,
            aws_account_id=aws_account.id
        ).filter(
            CachedBillingCollection.timestamp >= oldest_usable_cached_result_timestamp
        ).order_by(
            CachedBillingCollection.timestamp.desc()
        ).first()

        # If billing collection exists format and return it
        if billing_collection:
            # Create a service breakdown list from database data
            service_breakdown_list = []

            for billing_item in billing_collection.billing_items:
                service_breakdown_list.append({
                    "service_name": billing_item.service_name,
                    "unit": billing_item.unit,
                    "total": billing_item.total,
                })

            dbsession.close()
            # XXX Early return
            return service_breakdown_list

    # Pull the raw billing data via the AWS CostExplorer API
    # Note that this returned data is not marked up.
    # This also costs us 1 cent each time we make this request
    # Which is why we implement caching for user billing.
    service_breakdown_list = api_get_sub_account_billing_data(
        app_config,
        db_session_maker,
        aws_cost_explorer,
        aws_client_factory,
        account_id,
        account_type,
        start_date,
        end_date,
        granularity,
    )

    # Since we've queried this data we'll cache it for future
    # retrievals.
    new_billing_collection = CachedBillingCollection()
    new_billing_collection.billing_start_date = start_date
    new_billing_collection.billing_end_date = end_date
    new_billing_collection.billing_granularity = granularity
    new_billing_collection.aws_account_id = aws_account.id

    # Add all of the line items as billing items
    for service_breakdown_data in service_breakdown_list:
        billing_item = CachedBillingItem()
        billing_item.service_name = service_breakdown_data["service_name"]
        billing_item.unit = service_breakdown_data["unit"]
        billing_item.total = service_breakdown_data["total"]
        new_billing_collection.billing_items.append(
            billing_item
        )

    dbsession.add(new_billing_collection)
    dbsession.commit()
    dbsession.close()

    return service_breakdown_list


def api_get_sub_account_billing_data(app_config, db_session_maker, aws_cost_explorer, aws_client_factory,
                                     account_id, account_type, start_date, end_date, granularity):
    """
    account_id: 994344292413
    start_date: 2017-05-01
    end_date: 2017-06-01
    granularity: "daily" || "hourly" || "monthly"
    """
    metric_name = "NetUnblendedCost"

    and_statements = [
        {
            "Not": {
                "Dimensions": {
                    "Key": "RECORD_TYPE",
                    "Values": [
                        "Credit"
                    ]
                }
            }
        }
    ]

    billing_client = None
    if account_type == "MANAGED":
        and_statements.append({
            "Dimensions": {
                "Key": "LINKED_ACCOUNT",
                "Values": [
                    str(account_id)
                ]
            }
        })
        billing_client = aws_cost_explorer
    elif account_type == "THIRDPARTY":
        # For third party we need to do an assume role into the account
        dbsession = db_session_maker()
        aws_account = dbsession.query(AWSAccount).filter_by(
            account_id=account_id
        ).first()
        aws_account_dict = aws_account.to_dict()
        dbsession.close()

        billing_client = aws_client_factory.get_aws_client(
            "ce",
            aws_account_dict
        )

        and_statements.append({
            "Tags": {
                "Key": "RefineryResource",
                "Values": [
                    "true"
                ]
            }
        })

    if billing_client is None:
        raise Exception(
            "billing_client not set due to unhandled account type: {}".format(account_type))

    usage_parameters = {
        "TimePeriod": {
            "Start": start_date,
            "End": end_date,
        },
        "Filter": {
            "And": and_statements
        },
        "Granularity": granularity.upper(),
        "Metrics": [metric_name],
        "GroupBy": [
            {
                "Type": "DIMENSION",
                "Key": "SERVICE"
            }
        ]
    }

    logit("Parameters: ")
    logit(usage_parameters)

    try:
        response = billing_client.get_cost_and_usage(
            **usage_parameters
        )
    except ClientError as e:
        send_email(
            app_config,
            app_config.get("alerts_email"),
            "[Billing Notification] The Refinery AWS Account #" +
            account_id + " Encountered An Error When Calculating the Bill",
            "See HTML email.",
            render(
                app_config.get("EMAIL_TEMPLATES")["billing_error_email"],
                {
                    "account_id": account_id,
                    "code": e.response["Error"]["Code"],
                    "message": e.response["Error"]["Message"],
                }
            ),
        )
        return []

    logit("Cost and usage resonse: ")
    logit(response)

    cost_groups = response["ResultsByTime"][0]["Groups"]

    service_breakdown_list = []

    for cost_group in cost_groups:
        cost_group_name = cost_group["Keys"][0]
        unit = cost_group["Metrics"][metric_name]["Unit"]
        total = cost_group["Metrics"][metric_name]["Amount"]
        service_breakdown_list.append({
            "service_name": cost_group_name,
            "unit": unit,
            "total": total,
        })

    return service_breakdown_list


def get_sub_account_billing_forecast(app_config, aws_cost_explorer, account_id, start_date, end_date, granularity):
    """
    account_id: 994344292413
    start_date: 2017-05-01
    end_date: 2017-06-01
    granularity: monthly"
    """
    metric_name = "NET_UNBLENDED_COST"

    # Markup multiplier
    markup_multiplier = 1 + \
        (int(app_config.get("mark_up_percent")) / 100)

    forcecast_parameters = {
        "TimePeriod": {
            "Start": start_date,
            "End": end_date,
        },
        "Filter": {
            "Dimensions": {
                "Key": "LINKED_ACCOUNT",
                "Values": [
                    str(account_id)
                ]
            }
        },
        "Granularity": granularity.upper(),
        "Metric": metric_name
    }

    response = aws_cost_explorer.get_cost_forecast(
        **forcecast_parameters
    )

    forecast_total = float(response["Total"]["Amount"]) * markup_multiplier
    forecast_total_string = format_float_positional(forecast_total)
    forecast_unit = response["Total"]["Unit"]

    return {
        "forecasted_total": forecast_total_string,
        "unit": forecast_unit
    }
