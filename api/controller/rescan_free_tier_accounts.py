from tornado import gen
from controller.base import BaseHandler
from models.aws_accounts import AWSAccount
from models.initiate_database import DBSession
from models.users import User, RefineryUserTier

from utils.general import logit
from utils.free_tier import usage_spawner
from utils.free_tier import free_tier_freezer

@gen.coroutine
def scan_aws_accounts( frozen_aws_accounts ):
	# Unfreeze all of the accounts that are no longer over their quotas.
	for frozen_aws_account in frozen_aws_accounts:
		free_tier_info = yield usage_spawner.get_usage_data(
			frozen_aws_account
		)

		if free_tier_info[ "is_over_limit" ] == False:
			logit( "Unfreezing '" + frozen_aws_account[ "account_id" ] + "'..." )
			free_tier_freezer.unfreeze_aws_account(
				frozen_aws_account
			)

class RescanFreeTierAccounts( BaseHandler ):
	@gen.coroutine
	def get( self ):
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
		dbsession = DBSession()
		frozen_aws_accounts_rows = dbsession.query( AWSAccount ).filter_by(
			is_frozen=True
		).all()
		frozen_aws_accounts = []
		for frozen_aws_account_row in frozen_aws_accounts_rows:
			frozen_aws_accounts.append(
				frozen_aws_account_row.to_dict()
			)
		dbsession.close()

		if len(frozen_aws_accounts) == 0:
			logit( "No AWS accounts need unfreezing." )
			raise gen.Return()

		logit( str(len(frozen_aws_accounts)) + " are currently frozen, checking if we can unfreeze them..." )

		yield scan_aws_accounts(frozen_aws_accounts)