from tornado import gen
from controller.base import BaseHandler
from jsonschema import validate as validate_schema

from models.initiate_database import DBSession
from models.users import User, RefineryUserTier

from utils.general import logit
from utils.billing import billing_spawner
from utils.free_tier import usage_spawner, free_tier_freezer
from utils.terraform import terraform_spawner, TerraformSpawner

class UpgradeAccountTier( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Changes an account's tier from free->paid.

		Validates that the upgrade is indeed possible
		by checking that a valid payment method exists, etc.

		To go from paid->free we'll have to ask them to
		contact support so that we can be sure the outstanding
		billing amount has been collected.
		"""
		schema = {
			"type": "object",
			"properties": {
				"tier": {
					"type": "string",
					"enum": ["paid"]
				}
			},
			"required": [
				"tier"
			]
		}
		
		validate_schema( self.json, schema )

		current_user = self.get_authenticated_user()

		if current_user.tier == RefineryUserTier.PAID:
			self.write({
				"success": False,
				"code": "ALREADY_PAID_TIER",
				"msg": "Your account is already on the paid-tier, no need to upgrade.",
			})
			raise gen.Return()

		user_payment_cards = yield billing_spawner.get_account_cards(
			current_user.payment_id,
		)

		if len( user_payment_cards ) == 0:
			self.write({
				"success": False,
				"code": "NO_PAYMENT_INFORMATION",
				"msg": "You have no payment methods on file so you can't be upgraded to the paid tier!",
			})
			raise gen.Return()

		# Update account in database to be on the paid tier
		dbsession = DBSession()
		current_user.tier = RefineryUserTier.PAID 
		self.dbsession.commit()

		credentials = self.get_authenticated_user_cloud_configuration()

		# We do a terraform apply to the account to add the dedicate redis
		# instance that users get as part of being part of the paid-tier.
		logit( "Running 'terraform apply' against AWS Account " + credentials[ "account_id" ] )

		try:
			yield terraform_spawner.terraform_update_aws_account(
				credentials,
				"IN_USE"
			)
		except Exception as e:
			account_id = credentials[ "account_id" ]
			logit( "An unexpected error occurred while upgrading account tier for AWS account " + account_id )
			logit( e )
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