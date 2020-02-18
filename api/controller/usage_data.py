import datetime
from dateutil import relativedelta
from tornado import gen
from controller.base import BaseHandler
from sqlalchemy.sql import func

from models.lambda_executions import LambdaExecutions

from utils.general import logit

def get_first_day_of_month():
	today = datetime.date.today()
	if today.day > 25:
		today += datetime.timedelta(7)
	return today.replace(day=1)

def get_first_day_of_next_month():
	first_day_of_month = get_first_day_of_month()

	return first_day_of_month + relativedelta.relativedelta(months=1)

class GetUsageData( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		Returns up-to-date usage information for the user.

		This is for displaying to the user how much of their
		free-tier they've used up in Lambda execution time.
		"""
		"""
		schema = {
			"type": "object",
			"properties": {
				"account_id": {
					"type": "string",
				}
			},
			"required": []
		}
		
		validate_schema( self.json, schema )
		"""

		credentials = self.get_authenticated_user_cloud_configuration()

		# Get timestamp window for the beggining of this month to
		# the end of this month. We use this to filter only the
		# relevant executions for this month.
		first_day_of_month_timestamp = int(
			get_first_day_of_month().strftime("%s")
		)
		first_day_of_next_month_timestamp = int(
			get_first_day_of_next_month().strftime("%s")
		)

		# Get the 10 most recent Lambda executions to give the user an 
		# idea of what is currently costing them free-credits/money.
		recent_executions = self.dbsession.query( LambdaExecutions ).filter_by(
			account_id=credentials[ "account_id" ]
		).filter(
			LambdaExecutions.timestamp<=first_day_of_next_month_timestamp
		).limit(10).all()

		# Get the total Lambda execution time used this month
		# This returns a tuple of the billed duration time in millisecond(s)
		# along with the Lambda memory allocated. We multiple these together
		# in order to get the GB seconds used.
		lambda_executions = self.dbsession.query( LambdaExecutions ).filter_by(
			account_id=credentials[ "account_id" ]
		).filter(
			LambdaExecutions.timestamp<=first_day_of_next_month_timestamp
		).with_entities(
			LambdaExecutions.billed_duration,
			LambdaExecutions.memory_size,
		).all()

		# Total number of executions
		total_executions = len( lambda_executions )

		# Our counter for total GB/seconds used this month
		total_gb_milliseconds_used = 0

		for lambda_execution in lambda_executions:
			billed_exec_duration_ms = lambda_execution[0]
			billed_exec_mb = lambda_execution[1]

			total_gb_milliseconds_used += (
				billed_exec_duration_ms * billed_exec_mb
			)

		total_gb_seconds_used = total_gb_milliseconds_used / 1000
		print( "Total GB/second(s) used: " )
		print( total_gb_seconds_used )


		# Create recent execution(s) list
		recent_executions_list = []

		# Whitelisted keys to return for recent executions
		whitelisted_recent_execution_keys = [
			"lambda_name",
			"execution_timestamp",
			"duration",
			"billed_duration",
			"memory_size",
			"max_memory_used",
			"timestamp"
		]

		for recent_execution in recent_executions:
			recent_execution_dict = recent_execution.to_dict()
			filtered_execution_dict = {}

			for whitelisted_key in whitelisted_recent_execution_keys:
				filtered_execution_dict[ whitelisted_key ] = recent_execution_dict[ whitelisted_key ]

			recent_executions_list.append(filtered_execution_dict)

		self.write({
			"success": True,
			"result": {
				"totals": {
					"gb_seconds": total_gb_seconds_used,
					"gb_milliseconds": total_gb_milliseconds_used,
					"executions": total_executions
				},
				"recent": recent_executions_list
			}
		})