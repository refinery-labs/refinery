from models import AWSAccount
from models.users import RefineryUserTier, User
from utils.base_spawner import BaseSpawner


class AwsAccountPoolEmptyException(BaseException):
    pass


def is_free_tier_account(dbsession, credentials):
    # Check if the user is a MANAGED account, if not
    # then they can't be free-tier.
    if credentials[ "account_type" ] != "MANAGED":
        return False

    # Pull the organization users and check if any
    # are paid tier.
    organization_id = credentials[ "organization_id" ]

    # If there's no organization associated with the account
    # then it's free-tier by default.
    if not organization_id:
        return True

    org_users = [
        org_user
        for org_user in dbsession.query(User).filter_by(
            organization_id=organization_id
        ).all()
    ]

    # Default to the user not being paid tier
    # unless we are proven differently
    is_paid_tier = False
    for org_user in org_users:
        if org_user.tier == RefineryUserTier.PAID:
            is_paid_tier = True

    is_free_tier = not is_paid_tier

    return is_free_tier


class AwsAccountPoolManager(BaseSpawner):
    def __init__(self, aws_cloudwatch_client, logger, aws_account_freezer, app_config):
        super().__init__(aws_cloudwatch_client, logger, app_config=app_config)

        self.aws_account_freezer = aws_account_freezer

    def reserve_aws_account_for_organization(self, dbsession, organization_id):
        # Check if there are reserved AWS accounts available
        aws_reserved_account = dbsession.query(AWSAccount).filter_by(
            aws_account_status="AVAILABLE"
        ).first()

        if aws_reserved_account is None:
            raise AwsAccountPoolEmptyException()

        self.logger("Adding a reserved AWS account to the newly registered Refinery account...")
        aws_reserved_account.aws_account_status = "IN_USE"
        aws_reserved_account.organization_id = organization_id

        # Don't yield because we don't care about the result
        # Unfreeze/thaw the account so that it's ready for the new user
        # This takes ~30 seconds - worth noting. But that **should** be fine.
        self.aws_account_freezer.unfreeze_aws_account(
            aws_reserved_account.to_dict()
        )

        dbsession.commit()
