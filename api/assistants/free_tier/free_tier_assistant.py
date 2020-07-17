import datetime

from dateutil import relativedelta
from tornado.concurrent import run_on_executor

from utils.base_spawner import BaseSpawner

from models.lambda_executions import LambdaExecutions
from models.users import User, RefineryUserTier


class AwsMonthTotals:
	def __init__(
			self,
			gb_seconds=0.0,
			gb_milliseconds=0,
			executions=0,
			remaining_gb_seconds=0
	):
		self.gb_seconds = gb_seconds
		self.gb_milliseconds = gb_milliseconds
		self.executions = executions
		self.remaining_gb_seconds = remaining_gb_seconds

	def serialize(self):
		return {
			"gb_seconds": self.gb_seconds,
			"gb_milliseconds": self.gb_milliseconds,
			"executions": self.executions,
			"remaining_gb_seconds": self.remaining_gb_seconds
		}


class AwsUsageData:
	def __init__(
			self,
			month_totals,
			is_free_tier_user=False,
			is_over_limit=False,
			is_frozen=False,
			recent_executions=[]
	):
		self.is_free_tier_user = is_free_tier_user
		self.is_over_limit = is_over_limit
		self.is_frozen = is_frozen
		self.recent_executions = recent_executions
		self.month_totals = month_totals

	def serialize(self):
		return {
			"is_free_tier_user": self.is_free_tier_user,
			"is_over_limit": self.is_over_limit,
			"is_frozen": self.is_frozen,
			"recent_executions": self.recent_executions,
			"month_totals": self.month_totals.serialize(),
		}


def get_first_day_of_month():
	today = datetime.date.today()
	if today.day > 25:
		today += datetime.timedelta(7)
	return today.replace(day=1)


def get_first_day_of_next_month():
	first_day_of_month = get_first_day_of_month()

	return first_day_of_month + relativedelta.relativedelta(months=1)


class UsageSpawner(BaseSpawner):
	def __init__(self, aws_cloudwatch_client, logger, app_config, db_session_maker):
		super().__init__(self, aws_cloudwatch_client, logger, app_config)

		self.db_session_maker = db_session_maker

		# The maximum number of GB-seconds a free-tier user can use
		# before their deployments are frozen to prevent any further
		# resource usage.
		self._free_tier_monthly_max_gb_seconds = self.app_config.get("free_tier_monthly_max_gb_seconds")

	@staticmethod
	def _is_free_tier_account( db_session_maker, credentials ):
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

		dbsession = db_session_maker()
		org_users = [
			org_user
			for org_user in dbsession.query( User ).filter_by(
				organization_id=organization_id
			).all()
		]
		dbsession.close()

		# Default to the user not being paid tier
		# unless we are proven differently
		is_paid_tier = False
		for org_user in org_users:
			if org_user.tier == RefineryUserTier.PAID:
				is_paid_tier = True

		is_free_tier = not is_paid_tier

		return is_free_tier

	@run_on_executor
	def get_usage_data( self, credentials ) -> AwsUsageData:
		is_free_tier_account = UsageSpawner._is_free_tier_account(
			self.db_session_maker,
			credentials
		)

		if not is_free_tier_account:
			return AwsUsageData(
				month_totals=AwsMonthTotals(),
				is_frozen=credentials["is_frozen"]
			)

		# Get timestamp window for the beginning of this month to
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
		dbsession = self.db_session_maker()
		recent_executions = dbsession.query( LambdaExecutions ).filter_by(
			account_id=credentials[ "account_id" ]
		).filter(
			LambdaExecutions.timestamp <= first_day_of_next_month_timestamp
		).limit(10).all()

		# Get the total Lambda execution time used this month
		# This returns a tuple of the billed duration time in millisecond(s)
		# along with the Lambda memory allocated. We multiple these together
		# in order to get the GB seconds used.
		lambda_executions = dbsession.query( LambdaExecutions ).filter_by(
			account_id=credentials[ "account_id" ]
		).filter(
			LambdaExecutions.timestamp <= first_day_of_next_month_timestamp
		).with_entities(
			LambdaExecutions.billed_duration,
			LambdaExecutions.memory_size,
		).all()
		dbsession.close()

		# Total number of executions
		total_executions = len( lambda_executions )

		# Our counter for total GB/seconds used this month
		total_gb_milliseconds_used = 0

		for lambda_execution in lambda_executions:
			billed_exec_duration_ms = lambda_execution[0]
			billed_exec_mb = lambda_execution[1]

			# Get fraction of GB-second and multiply it by
			# the billed execution to get the total GB-seconds
			# used in milliseconds.
			gb_fraction = 1024 / billed_exec_mb

			total_gb_milliseconds_used += (
				gb_fraction * billed_exec_duration_ms
			)

		# Get total GB/seconds used
		total_gb_seconds_used = total_gb_milliseconds_used / 1000

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

		# Get the remaining free-tier GB-seconds the user has
		remaining_gb_seconds = self._free_tier_monthly_max_gb_seconds - total_gb_seconds_used

		# If they've gone over the max just return zero
		if remaining_gb_seconds < 0:
			remaining_gb_seconds = 0

		return AwsUsageData(
			month_totals=AwsMonthTotals(
				gb_seconds=total_gb_seconds_used,
				gb_milliseconds=total_gb_milliseconds_used,
				executions=total_executions,
				remaining_gb_seconds=remaining_gb_seconds
			),
			is_free_tier_user=True,
			is_over_limit=remaining_gb_seconds == 0,
			is_frozen=credentials["is_frozen"],
			recent_executions=recent_executions_list
		)
