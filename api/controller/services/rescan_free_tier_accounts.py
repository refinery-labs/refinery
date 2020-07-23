import pinject
from tornado import gen

from assistants.aws_account_management.account_freezer import AwsAccountFreezer
from assistants.aws_account_management.account_pool_manager import is_free_tier_account
from assistants.aws_account_management.account_usage_manager import AwsAccountUsageManager, \
    get_monthly_user_lambda_execution_report
from controller.base import BaseHandler
from models.aws_accounts import AWSAccount
from utils.db_session_scope import session_scope

from utils.general import logit


@gen.coroutine
def scan_aws_accounts(db_session_maker, aws_account_usage_manager: AwsAccountUsageManager, aws_account_freezer, frozen_aws_accounts):
    accounts_unfrozen = 0

    with session_scope(db_session_maker) as dbsession:
        # Unfreeze all of the accounts that are no longer over their quotas.
        for frozen_aws_account in frozen_aws_accounts:
            account_id = frozen_aws_account["account_id"]

            is_free_tier = is_free_tier_account(dbsession, frozen_aws_account)

            monthly_lambda_usage_report = get_monthly_user_lambda_execution_report(dbsession, account_id)

            lambda_usage_report_exists = monthly_lambda_usage_report is not None

            free_tier_info = aws_account_usage_manager.get_aws_usage_data(
                is_free_tier,
                monthly_lambda_usage_report
            )

            if not lambda_usage_report_exists or not free_tier_info.is_over_limit:
                logit(f"Unfreezing '{account_id}'...")
                aws_account_freezer.unfreeze_aws_account(
                    frozen_aws_account
                )
                accounts_unfrozen += 1

            # TODO cleanup lambda executions which fall outside of window?

    raise gen.Return(accounts_unfrozen)


class RescanFreeTierAccountsDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, aws_account_usage_manager, aws_account_freezer):
        pass


class RescanFreeTierAccounts(BaseHandler):
    dependencies = RescanFreeTierAccountsDependencies
    aws_account_usage_manager: AwsAccountUsageManager = None
    aws_account_freezer: AwsAccountFreezer = None

    @gen.coroutine
    def get(self):
        """
        This endpoint scans all free-tier accounts and unfreezes any
        which are no longer over their free-tier quota. This can be run
        on the first of every month (or every day) as it will only unfreeze
        accounts which have not exceeded their quota for the current month.
        """
        self.write({
            "success": True,
            "msg": "Free-tier frozen AWS account scanner started."
        })
        self.finish()

        # Get all AWS accounts that are currently frozen
        dbsession = self.db_session_maker()
        frozen_aws_accounts_rows = [
            row
            for row in dbsession.query(AWSAccount).filter_by(
                is_frozen=True
            ).all()
        ]
        dbsession.close()

        frozen_aws_accounts = []
        for frozen_aws_account_row in frozen_aws_accounts_rows:
            frozen_aws_accounts.append(
                frozen_aws_account_row.to_dict()
            )

        if len(frozen_aws_accounts) == 0:
            logit("No AWS accounts need unfreezing.")
            raise gen.Return()

        logit(str(len(frozen_aws_accounts)) + " are currently frozen, checking if we can unfreeze them...")

        accounts_unfrozen = yield scan_aws_accounts(
            self.db_session_maker,
            self.aws_account_usage_manager,
            self.aws_account_freezer,
            frozen_aws_accounts
        )

        logit(str(accounts_unfrozen) + " free-tier accounts have been unfrozen.")
