import datetime

from tornado import gen

from utils.general import logit


@gen.coroutine
def clear_sub_account_packages(task_spawner, credentials):
    # Delete up to 1000 pages of packages
    for _ in range(1000):
        package_paths = yield task_spawner.get_build_packages(
            credentials,
            "",
            1000
        )

        logit("Deleting #" + str(len(package_paths)) + " build packages for account ID " + credentials["account_id"] + "...")

        if len(package_paths) == 0:
            break

        yield task_spawner.bulk_s3_delete(
            credentials,
            credentials["lambda_packages_bucket"],
            package_paths
        )


def get_last_month_start_and_end_date_strings():
    """
    Returns the start date string of the previous month and
    the start date of the current month for pulling AWS
    billing for the last month.
    """
    # Get first day of last month
    today_date = datetime.date.today()
    one_month_ago_date = datetime.date.today() - datetime.timedelta(days=30)

    return {
        "current_date": today_date.strftime("%Y-%m-%d"),
        "month_start_date": one_month_ago_date.strftime("%Y-%m-01"),
        "next_month_first_day": today_date.strftime("%Y-%m-01"),
    }
