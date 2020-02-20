import os
import json
import tornado
import datetime
import botocore

from dateutil import relativedelta
from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen

from utils.base_spawner import BaseSpawner
from utils.general import get_urand_password
from utils.aws_client import get_aws_client

from models.lambda_executions import LambdaExecutions
from models.initiate_database import DBSession
from models.users import User, RefineryUserTier
from models.aws_accounts import AWSAccount

from pyconstants.customer_iam_policy import CUSTOMER_IAM_POLICY

# The maximum number of GB-seconds a free-tier user can use
# before their deployments are frozen to prevent any further
# resource usage.
FREE_TIER_MONTHLY_MAX_GB_SECONDS = int( os.environ.get( "free_tier_monthly_max_gb_seconds" ) )

def get_first_day_of_month():
	today = datetime.date.today()
	if today.day > 25:
		today += datetime.timedelta(7)
	return today.replace(day=1)

def get_first_day_of_next_month():
	first_day_of_month = get_first_day_of_month()

	return first_day_of_month + relativedelta.relativedelta(months=1)

class UsageSpawner(BaseSpawner):
	@staticmethod
	def _is_free_tier_account( credentials ):
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

		dbsession = DBSession()
		org_users = dbsession.query( User ).filter_by(
			organization_id=organization_id
		).all()

		# Default to the user not being paid tier
		# unless we are proven differently
		is_paid_tier = False
		for org_user in org_users:
			if org_user.tier == RefineryUserTier.PAID:
				is_paid_tier = True
		dbsession.close()

		return (
			is_paid_tier == False
		)

	@run_on_executor
	def get_usage_data( self, credentials ):
		is_free_tier_account = UsageSpawner._is_free_tier_account(
			credentials
		)

		if not is_free_tier_account:
			return {
				"is_free_tier_user": False,
				"is_over_limit": False,
				"is_frozen": credentials[ "is_frozen" ],
				"month_totals": {
					"gb_seconds": 0,
					"gb_milliseconds": 0,
					"executions": 0,
					"remaining_gb_seconds": 0
				},
				"recent_executions": []
			}

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
		dbsession = DBSession()
		recent_executions = dbsession.query( LambdaExecutions ).filter_by(
			account_id=credentials[ "account_id" ]
		).filter(
			LambdaExecutions.timestamp<=first_day_of_next_month_timestamp
		).limit(10).all()
		dbsession.close()

		# Get the total Lambda execution time used this month
		# This returns a tuple of the billed duration time in millisecond(s)
		# along with the Lambda memory allocated. We multiple these together
		# in order to get the GB seconds used.
		dbsession = DBSession()
		lambda_executions = dbsession.query( LambdaExecutions ).filter_by(
			account_id=credentials[ "account_id" ]
		).filter(
			LambdaExecutions.timestamp<=first_day_of_next_month_timestamp
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
		remaining_gb_seconds = FREE_TIER_MONTHLY_MAX_GB_SECONDS - total_gb_seconds_used

		# If they've gone over the max just return zero
		if remaining_gb_seconds < 0:
			remaining_gb_seconds = 0

		return {
			"is_free_tier_user": True,
			"is_over_limit": ( remaining_gb_seconds == 0 ),
			"is_frozen": credentials[ "is_frozen" ],
			"month_totals": {
				"gb_seconds": total_gb_seconds_used,
				"gb_milliseconds": total_gb_milliseconds_used,
				"executions": total_executions,
				"remaining_gb_seconds": remaining_gb_seconds
			},
			"recent_executions": recent_executions_list
		}

usage_spawner = UsageSpawner()

class FreeTierFreezerSpawner(BaseSpawner):
	@run_on_executor
	def freeze_aws_account( self, credentials ):
		return FreeTierFreezerSpawner._freeze_aws_account( credentials )
	
	@staticmethod
	def _freeze_aws_account( credentials ):
		"""
		Freezes an AWS sub-account when the user exceeds their free-tier
		monthly-quota.

		The steps are as follows:
		* Disable AWS console access by changing the password
		* Revoke all active AWS console sessions
		* Iterate over all deployed Lambdas and throttle them
		* Stop all active CodeBuilds
		"""
		logit( "Freezing AWS account..." )
		
		# Rotate and log out users from the AWS console
		new_console_user_password = FreeTierFreezerSpawner._recreate_aws_console_account(
			credentials,
			True
		)
		
		# Update the console login in the database
		dbsession = DBSession()
		aws_account = dbsession.query( AWSAccount ).filter_by(
			account_id=credentials[ "account_id" ]
		).first()
		aws_account.iam_admin_password = new_console_user_password
		dbsession.commit()
		dbsession.close()

		# Get Lambda ARNs
		lambda_arn_list = FreeTierFreezerSpawner.get_lambda_arns( credentials )

		FreeTierFreezerSpawner.set_zero_concurrency_for_lambdas(
			credentials,
			lambda_arn_list
		)

		FreeTierFreezerSpawner.stop_all_codebuilds(
			credentials
		)

		FreeTierFreezerSpawner.stop_all_ec2_instances(
			credentials
		)

		dbsession = DBSession()
		aws_account = dbsession.query( AWSAccount ).filter_by(
			account_id=credentials[ "account_id" ]
		).first()
		aws_account.is_frozen = True
		dbsession.commit()
		dbsession.close()

		logit( "Account freezing complete, stay frosty!" )

		return False

	@staticmethod
	def stop_all_ec2_instances( credentials ):
		ec2_client = get_aws_client(
			"ec2",
			credentials
		)

		ec2_instance_ids = FreeTierFreezerSpawner.get_ec2_instance_ids( credentials )

		stop_instance_response = ec2_client.stop_instances(
			InstanceIds=ec2_instance_ids
		)

	@staticmethod
	def stop_all_codebuilds( credentials ):
		codebuild_client = get_aws_client(
			"codebuild",
			credentials
		)

		# List all CodeBuild builds and stop any that are running
		codebuild_build_ids = []
		codebuild_list_params = {}
		
		while True:
			codebuild_list_response = codebuild_client.list_builds(
				**codebuild_list_params
			)
			
			for build_id in codebuild_list_response[ "ids" ]:
				codebuild_build_ids.append(
					build_id
				)
			
			if not ( "nextToken" in codebuild_list_response ):
				break
			
			codebuild_list_params[ "nextToken" ] = codebuild_list_response[ "nextToken" ]
		
		# We now scan these builds to see if they are currently running.
		# We can do this in batches of 100
		active_build_ids = []
		chunk_size = 100
		
		while len( codebuild_build_ids ) > 0:
			chunk_of_build_ids = codebuild_build_ids[:chunk_size]
			remaining_build_ids = codebuild_build_ids[chunk_size:]
			codebuild_build_ids = remaining_build_ids
			
			# Pull the information for the build ID chunk
			builds_info_response = codebuild_client.batch_get_builds(
				ids=chunk_of_build_ids,
			)
			
			# Iterate over the builds info response to find live build IDs
			for build_info in builds_info_response[ "builds" ]:
				if build_info[ "buildStatus" ] == "IN_PROGRESS":
					active_build_ids.append(
						build_info[ "id" ]
					)
		
		# Run through all active builds and stop them in their place
		for active_build_id in active_build_ids:
			stop_build_response = codebuild_client.stop_build(
				id=active_build_id
			)
		
	@run_on_executor
	def recreate_aws_console_account( self, credentials, rotate_password ):
		return FreeTierFreezerSpawner._recreate_aws_console_account(
			credentials,
			rotate_password
		)
		
	@staticmethod
	def _recreate_aws_console_account( credentials, rotate_password ):
		iam_client = get_aws_client(
			"iam",
			credentials
		)
		
		# The only way to revoke an AWS Console user's session
		# is to delete the console user and create a new one.
		
		# Generate the IAM policy ARN
		iam_policy_arn = "arn:aws:iam::" + credentials[ "account_id" ] + ":policy/RefineryCustomerPolicy"
		
		logit( "Deleting AWS console user..." )
		
		try:
			# Delete the current AWS console user
			delete_user_profile_response = iam_client.delete_login_profile(
				UserName=credentials[ "iam_admin_username" ],
			)
		except:
			logit( "Error deleting login profile, continuing...")
	
		try:
			# Remove the policy from the user
			detach_user_policy = iam_client.detach_user_policy(
				UserName=credentials[ "iam_admin_username" ],
				PolicyArn=iam_policy_arn
			)
		except:
			logit( "Error detaching user policy, continuing..." )
		
		try:
			# Delete the IAM user
			delete_user_response = iam_client.delete_user(
				UserName=credentials[ "iam_admin_username" ],
			)
		except:
			logit( "Error deleting user, continuing..." )
		
		logit( "Re-creating the AWS console user..." )
		
		# Create the IAM user again
		delete_user_response = iam_client.create_user(
			UserName=credentials[ "iam_admin_username" ],
		)
		
		try:
			# Delete the IAM policy
			delete_policy_response = iam_client.delete_policy(
				PolicyArn=iam_policy_arn
			)
		except:
			logit( "Error deleting IAM policy, continuing..." )
		
		# Create IAM policy for the user
		create_policy_response = iam_client.create_policy(
			PolicyName="RefineryCustomerPolicy",
			PolicyDocument=json.dumps( CUSTOMER_IAM_POLICY ),
			Description="Refinery Labs managed AWS customer account policy."
		)
		
		# Attach the limiting IAM policy to it.
		attach_policy_response = iam_client.attach_user_policy(
			UserName=credentials[ "iam_admin_username" ],
			PolicyArn=iam_policy_arn
		)
			
		# Generate a new user console password
		new_console_user_password = get_urand_password( 32 )
		
		if rotate_password == False:
			new_console_user_password = credentials[ "iam_admin_password" ]
	
		# Create the console user again.
		create_user_response = iam_client.create_login_profile(
			UserName=credentials[ "iam_admin_username" ],
			Password=new_console_user_password,
			PasswordResetRequired=False
		)
			
		return new_console_user_password
		
	@run_on_executor
	def unfreeze_aws_account( self, credentials ):
		return FreeTierFreezerSpawner._unfreeze_aws_account(
			credentials
		)
	
	@staticmethod
	def _unfreeze_aws_account( credentials ):
		"""
		Unfreezes a previously-frozen AWS account, this is for situations
		where a user has gone over their free-trial or billing limit leading
		to their account getting frozen. By calling this the account will be
		re-enabled for regular Refinery use.
		* De-throttle all AWS Lambdas
		* Turn on EC2 instances (redis)
		"""
		logit( "Unfreezing AWS account..." )
		
		lambda_client = get_aws_client(
			"lambda",
			credentials
		)
		
		ec2_client = get_aws_client(
			"ec2",
			credentials
		)
		
		# Pull all Lambda ARN(s)
		lambda_arns = FreeTierFreezerSpawner.get_lambda_arns(
			credentials
		)

		FreeTierFreezerSpawner.remove_lambda_concurrency_limits(
			credentials,
			lambda_arns
		)
		
		# Start EC2 instance(s)
		ec2_instance_ids = FreeTierFreezerSpawner.get_ec2_instance_ids( credentials )
		
		FreeTierFreezerSpawner.start_ec2_instances(
			credentials,
			ec2_instance_ids
		)

		logit( "Unfreezing of account is complete!" )

		dbsession = DBSession()
		aws_account = dbsession.query( AWSAccount ).filter_by(
			account_id=credentials[ "account_id" ]
		).first()
		aws_account.is_frozen = False
		dbsession.commit()
		dbsession.close()
		
		return True

	@staticmethod
	def start_ec2_instances( credentials, ec2_instance_ids ):
		ec2_client = get_aws_client(
			"ec2",
			credentials
		)

		# Max attempts
		remaining_attempts = 20

		# Prevents issue if a freeze happens too quickly after an un-freeze
		while remaining_attempts > 0:
			try:
				start_instance_response = ec2_client.start_instances(
					InstanceIds=ec2_instance_ids
				)
			except botocore.exceptions.ClientError as boto_error:
				if boto_error.response[ "Error" ][ "Code" ] != "IncorrectInstanceState":
					raise
				
				logit( "EC2 instance isn't ready to be started yet!" )
				logit( "Waiting 2 seconds and trying again..." )
				time.sleep(2)
				
			remaining_attempts = remaining_attempts - 1
		
	@staticmethod
	def get_lambda_arns( credentials ):
		lambda_client = get_aws_client(
			"lambda",
			credentials
		)
		
		# Now we throttle all of the user's Lambdas so none will execute
		# First we pull all of the user's Lambdas
		lambda_list_params = {
			"MaxItems": 50,
		}
		
		# The list of Lambda ARNs
		lambda_arn_list = []
		
		while True:
			lambda_functions_response = lambda_client.list_functions(
				**lambda_list_params
			)
			
			for lambda_function_data in lambda_functions_response[ "Functions" ]:
				lambda_arn_list.append(
					lambda_function_data[ "FunctionArn" ]
				)
			
			# Only do another loop if we have more results
			if not ( "NextMarker" in lambda_functions_response ):
				break
			
			lambda_list_params[ "Marker" ] = lambda_functions_response[ "NextMarker" ]
			
		return lambda_arn_list

	@staticmethod
	def remove_lambda_concurrency_limits( credentials, lambda_arn_list ):
		"""
		Note their is a subtle bug here:

		If someone sets reserved concurrency for their Lambda and their
		account is frozen and unfrozen then they will lose the concurrency
		limit upon the account being unfrozen.

		Potential fixes:
		* Prevent setting concurrency for free-accounts (would make sence given
		they'd already have limited concurrency).
		* Consult the deployment diagrams to get the Lambdas pre-freeze concurrency
		limit.
		"""
		lambda_client = get_aws_client(
			"lambda",
			credentials
		)

		# Remove function throttle from each Lambda
		for lambda_arn in lambda_arn_list:
			lambda_client.delete_function_concurrency(
				FunctionName=lambda_arn
			)

	@staticmethod
	def set_zero_concurrency_for_lambdas( credentials, lambda_arn_list ):
		lambda_client = get_aws_client(
			"lambda",
			credentials
		)

		# Iterate over list of Lambda ARNs and set concurrency to zero for all
		for lambda_arn in lambda_arn_list:
			lambda_client.put_function_concurrency(
				FunctionName=lambda_arn,
				ReservedConcurrentExecutions=0
			)

		return True

	@staticmethod
	def get_ec2_instance_ids( credentials ):
		ec2_client = get_aws_client(
			"ec2",
			credentials
		)
		
		# Turn off all EC2 instances (AKA just redis)
		ec2_describe_instances_response = ec2_client.describe_instances(
			MaxResults=1000
		)

		# List of EC2 instance IDs
		ec2_instance_ids = []
		
		for ec2_instance_data in ec2_describe_instances_response[ "Reservations" ][0][ "Instances" ]:
			ec2_instance_ids.append(
				ec2_instance_data[ "InstanceId" ]
			)
			
		return ec2_instance_ids

free_tier_freezer = FreeTierFreezerSpawner()