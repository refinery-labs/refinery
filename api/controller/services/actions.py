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
