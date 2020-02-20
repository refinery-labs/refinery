from tornado import gen
from controller.base import BaseHandler

from models.lambda_executions import LambdaExecutions
from models.initiate_database import DBSession
from models.aws_accounts import AWSAccount

from utils.general import logit
from utils.free_tier import usage_spawner
from utils.free_tier import free_tier_freezer
from sqlalchemy.exc import IntegrityError
from jsonschema import validate as validate_schema

class StoreLambdaExecutionDetails( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		The inbound JSON POST data is the following format:
		{
		  "account_id": "956509444157",
		  "log_name": "/aws/lambda/ayylmao_RFNzCKWzW0",
		  "log_stream": "2020/02/13/[$LATEST]1095083dde2e442286e0586fa06cdcb9",
		  "lambda_name": "ayylmao_RFNzCKWzW0",
		  "raw_line": "REPORT RequestId: 4ae7bd66-84d5-44db-93f5-b52f4323926e\tDuration: 1091.32 ms\tBilled Duration: 1800 ms\tMemory Size: 576 MB\tMax Memory Used: 124 MB\tInit Duration: 698.39 ms\t\n",
		  "timestamp": 1581635332,
		  "timestamp_ms": 1581635332750,
		  "duration": "1091.32",
		  "memory_size": 576,
		  "max_memory_used": 124,
		  "billed_duration": 1800,
		  "report_requestid": "4ae7bd66-84d5-44db-93f5-b52f4323926e"
		}
		"""
		schema = {
			"type": "object",
			"properties": {
				"account_id": {
					"type": "string",
					"pattern": "[0-9]{12}"
				},
				"log_name": {
					"type": "string",
				},
				"log_stream": {
					"type": "string",
				},
				"lambda_name": {
					"type": "string",
				},
				"raw_line": {
					"type": "string",
				},
				"timestamp": {
					"type": "number",
				},
				"timestamp_ms": {
					"type": "number",
				},
				"duration": {
					"type": "string",
				},
				"memory_size": {
					"type": "number",
				},
				"max_memory_used": {
					"type": "number",
				},
				"billed_duration": {
					"type": "number",
				},
				"report_requestid": {
					"type": "string",
				}
			},
			"required": [
				"account_id",
				"log_name",
				"log_stream",
				"lambda_name",
				"raw_line",
				"timestamp",
				"timestamp_ms",
				"duration", 
				"memory_size",
				"max_memory_used",
				"billed_duration",
				"report_requestid"
			]
		}
		
		validate_schema( self.json, schema )

		new_execution = LambdaExecutions()
		new_execution.account_id = self.json[ "account_id" ]
		new_execution.log_name = self.json[ "log_name" ]
		new_execution.log_stream = self.json[ "log_stream" ]
		new_execution.lambda_name = self.json[ "lambda_name" ]
		new_execution.raw_line = self.json[ "raw_line" ]
		new_execution.execution_timestamp = self.json[ "timestamp" ]
		new_execution.execution_timestamp_ms = self.json[ "timestamp_ms" ]
		new_execution.duration = float( self.json[ "duration" ] )
		new_execution.memory_size = self.json[ "memory_size" ]
		new_execution.max_memory_used = self.json[ "max_memory_used" ]
		new_execution.billed_duration = self.json[ "billed_duration" ]
		new_execution.report_requestid = self.json[ "report_requestid" ]
		self.dbsession.add( new_execution )

		try:
			self.dbsession.commit()
		except IntegrityError as e:
			"""
			An expected error case is when we get an execution
			for an AWS account which is no longer in the database.

			This can happen specifically for third-party AWS accounts
			which are no longer managed by us but are still sending us
			their Lambda execution data. For these instances we just
			print a line about it occurring and suppress the full
			SQL exception.
			"""
			sql_error_message = str( e.orig )

			is_non_existent_aws_account = (
				"Key (account_id)=(" in sql_error_message
				and "is not present in table \"aws_accounts\"." in sql_error_message
			)

			if is_non_existent_aws_account:
				logit( "Received Lambda execution data for an AWS account we don't have a record of (" + self.json[ "account_id" ] + "). Ignoring it." )
				self.write({
					"success": False
				})
				raise gen.Return()

			# If it's not a non-existent AWS account issue
			# then we'll rethrow it
			raise

		# First pull the relevant AWS account
		aws_account = self.dbsession.query( AWSAccount ).filter_by(
			account_id=self.json[ "account_id" ],
		).first()
		credentials = aws_account.to_dict()

		# Pull their free-tier status
		free_tier_info = yield usage_spawner.get_usage_data(
			credentials
		)

		# If they've hit their free-tier limit we have to limit
		# their ability to deploy and freeze all of their current
		# Lambdas that they've deployed.
		#if free_tier_info[ "is_over_limit" ]:
		if True:
			logit("User " + self.json[ "account_id" ] + " is over their free-tier limit! Limiting their account...")

			# Kick off account freezer since user is over their limit
			yield free_tier_freezer.freeze_aws_account(
				credentials
			)

		self.write({
			"success": True
		})