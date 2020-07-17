from tornado import gen
from controller.base import BaseHandler
from jsonschema import validate as validate_schema

from models.users import User, RefineryUserTier
from models.aws_accounts import AWSAccount

from utils.general import logit


class DowngradeAccountTier(BaseHandler):
    @gen.coroutine
    def get(self):
        """
        Changes an account's tier from paid->free.
        This is available as a /service/ endpoint to
        allow
        """
        user_id = self.get_argument(
            "user_id",
            None,
            True
        )

        if user_id is None:
            self.write({
                "success": False,
                "code": "NO_ACCOUNT_SPECIFIED",
                "msg": "Please specify a 'user_id' parameter for which account we should downgrade to the free-tier.",
            })
            raise gen.Return()

        # Pull related user
        current_user = self.dbsession.query(User).filter_by(
            id=str(user_id)
        ).first()

        if current_user is None:
            self.write({
                "success": False,
                "code": "ACCOUNT_DOES_NOT_EXIST",
                "msg": "The ID provided does not correspond to a user account that exists in the database.",
            })
            raise gen.Return()

        if current_user.tier == RefineryUserTier.FREE:
            self.write({
                "success": False,
                "code": "ALREADY_FREE_TIER",
                "msg": "Your account is already on the paid-tier, no need to upgrade.",
            })
            raise gen.Return()

        # Update account in database to be on the paid tier
        dbsession = DBSession()
        current_user.tier = RefineryUserTier.FREE
        self.dbsession.commit()

        aws_account = self.dbsession.query(AWSAccount).filter_by(
            organization_id=current_user.organization_id,
            aws_account_status="IN_USE"
        ).first()

        if aws_account is None:
            self.write({
                "success": False,
                "code": "NO_AWS_ACCOUNT",
                "msg": "The specified account does not have an AWS account associated with it.",
            })
            raise gen.Return()

        credentials = aws_account.to_dict()

        # We do a terraform apply to the account to add the dedicate redis
        # instance that users get as part of being part of the paid-tier.
        logit("Running 'terraform apply' against AWS Account " + credentials["account_id"])

        try:
            yield terraform_spawner.terraform_update_aws_account(
                credentials,
                "IN_USE"
            )
        except Exception as e:
            account_id = credentials["account_id"]
            logit("An unexpected error occurred while upgrading account tier for AWS account " + account_id)
            logit(e)
            self.write({
                "success": False,
                "code": "RECONFIGURE_ERROR",
                "msg": "An unknown error occurred while upgrade your account to the paid tier. Please contact support!",
            })
            raise gen.Return()

        self.write({
            "success": True,
            "msg": "Successfully changed the account tier!"
        })
