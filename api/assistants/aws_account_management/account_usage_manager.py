from datetime import datetime, timedelta, date

from botocore.exceptions import ClientError
from time import time

import math

import pystache
from dateutil import relativedelta
from numpy import format_float_positional
from tornado.concurrent import run_on_executor
from typing import Union

from models import AWSAccount, Organization, CachedBillingCollection, CachedBillingItem
from models.lambda_execution_monthly_report import LambdaExecutionMonthlyReport
from tasks.email import send_email
from utils.base_spawner import BaseSpawner
from utils.db_session_scope import session_scope
from utils.general import logit
from utils.performance_decorators import emit_runtime_metrics


class AwsAccountForUsageNotFoundException(Exception):
    pass


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
    today = datetime.today()
    if today.day > 25:
        today += timedelta(7)
    return today.replace(day=1)


def get_first_day_of_next_month():
    first_day_of_month = get_first_day_of_month()

    return first_day_of_month + relativedelta.relativedelta(months=1)


def get_current_month_start_and_end_date_strings():
    """
    Returns the start date string of this month and
    the start date of the next month for pulling AWS
    billing for the current month.
    """
    # Get tomorrow date
    today_date = datetime.today()
    tomorrow_date = datetime.today() + timedelta(days=1)
    start_date = tomorrow_date

    # We could potentially be on the last day of the month
    # making tomorrow the next month! Check for this case.
    # If it's the case then we'll just set the start date to today
    if tomorrow_date.month == today_date.month:
        start_date = today_date

    # Get first day of next month
    current_month_num = today_date.month
    current_year_num = today_date.year
    next_month_num = current_month_num + 1

    # Check if we're on the last month
    # If so the next month number is 1
    # and we should add 1 to the year
    if current_month_num == 12:
        next_month_num = 1
        current_year_num = current_year_num + 1

    next_month_start_date = date(
        current_year_num,
        next_month_num,
        1
    )

    return {
        "current_date": tomorrow_date.strftime("%Y-%m-%d"),
        "month_start_date": tomorrow_date.strftime("%Y-%m-01"),
        "next_month_first_day": next_month_start_date.strftime("%Y-%m-%d"),
    }


def get_last_month_start_and_end_date_strings():
    """
    Returns the start date string of the previous month and
    the start date of the current month for pulling AWS
    billing for the last month.
    """
    # Get first day of last month
    today_date = datetime.today()
    one_month_ago_date = datetime.today() - timedelta(days=30)

    return {
        "current_date": today_date.strftime("%Y-%m-%d"),
        "month_start_date": one_month_ago_date.strftime("%Y-%m-01"),
        "next_month_first_day": today_date.strftime("%Y-%m-01"),
    }


def is_organization_first_month(db_session_maker, aws_account_id):
    # Pull the relevant organization from the database to check
    # how old the account is to know if the first-month's base fee should be applied.

    with session_scope(db_session_maker) as dbsession:
        aws_account = dbsession.query(
            Organization.timestamp
        ).join(
            AWSAccount
        ).filter_by(
            account_id=aws_account_id
        ).first()

        organization = dbsession.query(Organization).filter_by(
            id=aws_account.organization_id
        ).first()

        account_creation_dt = datetime.fromtimestamp(
            organization.timestamp
        )

    current_datetime = datetime.now()

    if account_creation_dt > (current_datetime - timedelta(days=40)):
        return True

    return False


def get_billing_rounded_float(input_price_float):
    """
    This is used because Stripe only allows you to charge line
    items in cents. Meaning that some rounding will occur on the
    final line items on the bill. AWS returns us lengthy-floats which
    means that the conversion will have to be done in both the invoice
    billing and the bill calculation endpoints the same way. We also have
    to do this in a safe round up way that won't accidentally under-bill
    our customers.

    This endpoint basically converts the AWS float into cents, rounds it,
    and then converts it back to a float rounded appropriately to two digits
    and returns the float again. All billing code should use this to ensure
    consistency in what the user sees from a billing point of view.
    """
    # Special case is when the input float is 0
    if input_price_float == 0:
        return float(0.00)

    # Round float UP TO second digit
    # Meaning 10.015 becomes 10.02
    # and 10.012 becomes 10.02
    rounded_up_float = (
            math.ceil(
                input_price_float * 100
            ) / 100
    )

    return rounded_up_float


def calculate_total_gb_seconds_used(billed_exec_duration_ms, exec_mb):
    # Get fraction of GB-second and multiply it by
    # the billed execution to get the total GB-seconds
    # used in milliseconds.
    gb_fraction = exec_mb / 1024
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


def get_monthly_user_lambda_execution_report(dbsession, account_id) -> Union[LambdaExecutionMonthlyReport, None]:
    # Get timestamp window for the beginning of this month to
    # the end of this month. We use this to filter only the
    # relevant executions for this month.
    first_day_of_month_timestamp = int(
        get_first_day_of_month().strftime("%s")
    )

    first_day_of_next_month_timestamp = int(
        get_first_day_of_next_month().strftime("%s")
    )

    print(first_day_of_month_timestamp, first_day_of_next_month_timestamp)

    lambda_execution_report: LambdaExecutionMonthlyReport = dbsession.query(LambdaExecutionMonthlyReport).filter_by(
        account_id=account_id
    ).filter(
        LambdaExecutionMonthlyReport.timestamp >= first_day_of_month_timestamp,
        LambdaExecutionMonthlyReport.timestamp <= first_day_of_next_month_timestamp
    ).first()

    return lambda_execution_report


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
    next_month_date = billing_month_datetime + datetime.timedelta(days=32)
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
                                 account_id, account_type, start_date, end_date, granularity, use_cache):
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

    # This is where we upgrade the billing total if it's not at least $5/mo
    # $5/mo is our floor price.
    if total_amount < 5.00 and not is_first_account_billing_month:
        amount_to_add = (5.00 - total_amount)
        return_data["service_breakdown"].append({
            "service_name": "Floor Fee (Bills are minimum $5/month, see refinery.io/pricing for more information).",
            "unit": "usd",
            "total": ("%.2f" % amount_to_add),
        })
        total_amount = 5.00

    return_data["bill_total"] = ("%.2f" % total_amount)

    return return_data


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
        if "NextPageToken" not in ce_response:
            break

        # If we have a next page token, then add it to our
        # parameters for the next paginated calls.
        ce_params["NextPageToken"] = ce_response["NextPageToken"]

    return aws_account_running_cost_list


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
    logit(str(usage_parameters))

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
            pystache.render(
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


class AwsAccountUsageManager(BaseSpawner):
    def __init__(self, aws_cloudwatch_client, logger, aws_client_factory, aws_cost_explorer, aws_account_freezer, db_session_maker, app_config):
        super().__init__(aws_cloudwatch_client, logger, app_config=app_config)

        self.aws_client_factory = aws_client_factory
        self.aws_cost_explorer = aws_cost_explorer
        self.aws_account_freezer = aws_account_freezer
        self.db_session_maker = db_session_maker

        # The maximum number of GB-seconds a free-tier user can use
        # before their deployments are frozen to prevent any further
        # resource usage.
        self.free_tier_monthly_max_gb_seconds = app_config.get("free_tier_monthly_max_gb_seconds")

    def get_aws_usage_data(self, is_free_tier_user, lambda_execution_report) -> AwsUsageData:
        # If the lambda execution report doesn't exist, then we are in a new month and able to unfreeze a user's account.
        if lambda_execution_report is None:
            return AwsUsageData(
                gb_seconds=0,
                remaining_gb_seconds=self.free_tier_monthly_max_gb_seconds,
                executions=0,
                is_over_limit=False
            )

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

    @staticmethod
    def get_or_create_lambda_monthly_report(dbsession, account_id, gb_seconds_used, executions) -> LambdaExecutionMonthlyReport:
        monthly_report = get_monthly_user_lambda_execution_report(dbsession, account_id)

        if monthly_report is None:
            monthly_report = LambdaExecutionMonthlyReport(account_id, gb_seconds_used)
            dbsession.add(monthly_report)
        else:
            monthly_report.gb_seconds_used += gb_seconds_used

        monthly_report.total_executions += executions

        dbsession.commit()

        return monthly_report

    @run_on_executor
    @emit_runtime_metrics("pull_current_month_running_account_totals")
    def pull_current_month_running_account_totals(self):
        return pull_current_month_running_account_totals(
            self.aws_cost_explorer
        )

    @run_on_executor
    @emit_runtime_metrics("get_sub_account_billing_forecast")
    def get_sub_account_billing_forecast(self, account_id, start_date, end_date, granularity):
        return get_sub_account_billing_forecast(
            self.app_config,
            self.aws_cost_explorer,
            account_id,
            start_date,
            end_date,
            granularity
        )

    @run_on_executor
    @emit_runtime_metrics("get_sub_account_month_billing_data")
    def get_sub_account_month_billing_data(self, account_id, account_type, billing_month, use_cache):
        return get_sub_account_month_billing_data(
            self.app_config,
            self.db_session_maker,
            self.aws_cost_explorer,
            self.aws_client_factory,
            account_id,
            account_type,
            billing_month,
            use_cache
        )



