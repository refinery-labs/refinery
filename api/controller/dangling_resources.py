from tornado import gen
from controller.base import BaseHandler
from utils.dangling_resources import get_user_dangling_resources

from models.initiate_database import *
from models.users import User
from models.aws_accounts import AWSAccount

from utils.deployments.teardown import teardown_infrastructure

from utils.general import logit

class CleanupDanglingResources( BaseHandler ):
	lambda_manager = None
	api_gateway_manager = None
	schedule_trigger_manager = None
	sns_manager = None
	sqs_manager = None

	def _initialize( self, lambda_manager, api_gateway_manager, schedule_trigger_manager, sns_manager, sqs_manager ):
		self.lambda_manager = lambda_manager
		self.api_gateway_manager = api_gateway_manager
		self.schedule_trigger_manager = schedule_trigger_manager
		self.sns_manager = sns_manager
		self.sqs_manager = sqs_manager

	@gen.coroutine
	def get( self, user_id=None ):
		delete_resources = self.get_argument( "confirm", False )

		# Get user's organization
		user = self.dbsession.query( User ).filter_by(
			id=user_id
		).first()

		if not user:
			self.write({
				"success": False,
				"msg": "No user was found with that UUID."
			})
			raise gen.Return()

		aws_account = self.dbsession.query( AWSAccount ).filter_by(
			organization_id=user.organization_id,
			aws_account_status="IN_USE"
		).first()

		if not aws_account:
			self.write({
				"success": False,
				"msg": "No AWS account found for user."
			})
			raise gen.Return()

		# Get credentials to perform scan
		credentials = aws_account.to_dict()

		# Get user dangling records
		dangling_resources = yield get_user_dangling_resources(
			self.db_session_maker,
			user_id,
			credentials
		)

		number_of_resources = len( dangling_resources )

		logit( str( len( dangling_resources ) ) + " resource(s) enumerated in account." )

		# If the "confirm" parameter is passed we can proceed to delete it all.
		if delete_resources:
			logit( "Deleting all dangling resources..." )

			# Tear down all dangling nodes
			teardown_results = yield teardown_infrastructure(
				self.api_gateway_manager,
				self.lambda_manager,
				self.schedule_trigger_manager,
				self.sns_manager,
				self.sqs_manager,
				credentials,
				dangling_resources
			)

			logit( teardown_results )

			logit( "Deleted all dangling resources successfully!" )

		self.write({
			"success": True,
			"total_resources": len( dangling_resources ),
			"result": dangling_resources
		})