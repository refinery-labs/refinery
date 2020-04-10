import base64
import copy
import csv
import datetime
import hashlib
import io
import json
import re
import shutil
import subprocess
import time
import traceback
import uuid
import zipfile

import boto3
import botocore
import numpy
import pinject
import pystache
import requests
import stripe
import tornado
import yaml
from botocore.exceptions import ClientError

from assistants.accounts import get_user_free_trial_information
from tornado.concurrent import run_on_executor, futures

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory
from assistants.deployments.ecs_builders import BuilderManager
from assistants.deployments.shared_files import add_shared_files_symlink_to_zip, add_shared_files_to_zip
from assistants.task_spawner.actions import get_current_month_start_and_end_date_strings, is_organization_first_month, \
	get_billing_rounded_float
from assistants.task_spawner.exceptions import InvalidLanguageException
from models import AWSAccount, Organization, CachedBillingCollection, CachedBillingItem, InlineExecutionLambda, User
from pyconstants.project_constants import EMPTY_ZIP_DATA, REGEX_WHITELISTS, THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME, LAMBDA_SUPPORTED_LANGUAGES
from pyexceptions.billing import CardIsPrimaryException
from pyexceptions.builds import BuildException
from utils.general import logit, get_urand_password, get_lambda_safe_name, log_exception
from utils.performance_decorators import emit_runtime_metrics

try:
	# for Python 2.x
	# noinspection PyCompatibility
	from StringIO import StringIO
except ImportError:
	# for Python 3.x
	from io import StringIO


# noinspection PyTypeChecker,SqlResolve
class TaskSpawner(object):
	app_config = None
	db_session_maker = None
	aws_cloudwatch_client = None
	aws_cost_explorer = None
	aws_organization_client = None
	aws_lambda_client = None
	api_gateway_manager = None
	lambda_manager = None
	logger = None
	schedule_trigger_manager = None
	sns_manager = None
	preterraform_manager = None
	aws_client_factory = None  # type: AwsClientFactory
	sts_client = None

	# noinspection PyUnresolvedReferences
	@pinject.copy_args_to_public_fields
	def __init__(
			self,
			app_config,
			db_session_maker,
			aws_cloudwatch_client,
			aws_cost_explorer,
			aws_organization_client,
			aws_lambda_client,
			api_gateway_manager,
			lambda_manager,
			logger,
			schedule_trigger_manager,
			sns_manager,
			preterraform_manager,
			aws_client_factory,
			sts_client,
			loop=None
	):
		self.executor = futures.ThreadPoolExecutor( 60 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	@emit_runtime_metrics( "create_third_party_aws_lambda_execute_role" )
	def create_third_party_aws_lambda_execute_role( self, credentials ):
		# Create IAM client
		iam_client = self.aws_client_factory.get_aws_client(
			"iam",
			credentials
		)

		assume_role_policy_doc = """
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "",
			"Effect": "Allow",
			"Principal": {
				"Service": "lambda.amazonaws.com"
			},
			"Action": "sts:AssumeRole"
		}
	]
}
"""
		# Create the AWS role for the account
		response = iam_client.create_role(
			RoleName=THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME,
			Description="The role that all Lambdas deployed with Refinery run as",
			MaxSessionDuration=(60 * 60),
			AssumeRolePolicyDocument=assume_role_policy_doc
		)

		response = iam_client.attach_role_policy(
			RoleName=THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME,
			PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
		)

		return True

	@run_on_executor
	@emit_runtime_metrics( "get_json_from_s3" )
	def get_json_from_s3( self, credentials, s3_bucket, s3_path ):
		# Create S3 client
		s3_client = self.aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		response = s3_client.get_object(
			Bucket=s3_bucket,
			Key=s3_path
		)

		return json.loads(
			response[ "Body" ].read()
		)

	@run_on_executor
	@emit_runtime_metrics( "write_json_to_s3" )
	def write_json_to_s3( self, credentials, s3_bucket, s3_path, input_data ):
		# Create S3 client
		s3_client = self.aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		response = s3_client.put_object(
			Bucket=s3_bucket,
			Key=s3_path,
			ACL="private",
			Body=json.dumps(
				input_data
			)
		)

	@run_on_executor
	@emit_runtime_metrics( "get_block_executions" )
	def get_block_executions( self, credentials, project_id, execution_pipeline_id, arn, oldest_timestamp ):
		return TaskSpawner._get_block_executions(
			self.aws_client_factory,
			credentials,
			project_id,
			execution_pipeline_id,
			arn,
			oldest_timestamp
		)

	@staticmethod
	def _get_block_executions( aws_client_factory, credentials, project_id, execution_pipeline_id, arn, oldest_timestamp ):
		project_id = re.sub( REGEX_WHITELISTS[ "project_id" ], "", project_id )
		timestamp_datetime = datetime.datetime.fromtimestamp( oldest_timestamp )

		query_template = """
		SELECT type, id, function_name, timestamp, dt
		FROM "refinery"."{{{project_id_table_name}}}"
		WHERE project_id = '{{{project_id}}}' AND
		arn = '{{{arn}}}' AND
		execution_pipeline_id = '{{{execution_pipeline_id}}}' AND
		dt > '{{{oldest_timestamp}}}'
		ORDER BY type, timestamp DESC
		"""

		# Since there's no parameterized querying for Athena we're gonna get ghetto with
		# the SQL injection mitigation. Joe, if you ever join this company or review this code
		# I blame this all on Free even though the git blame will say otherwise.
		query_template_data = {
			"execution_pipeline_id": re.sub( REGEX_WHITELISTS[ "execution_pipeline_id" ], "", execution_pipeline_id ),
			"project_id_table_name": "PRJ_" + project_id.replace( "-", "_" ),
			"arn": re.sub( REGEX_WHITELISTS[ "arn" ], "", arn ),
			"project_id": re.sub( REGEX_WHITELISTS[ "project_id" ], "", project_id ),
			"oldest_timestamp": timestamp_datetime.strftime( "%Y-%m-%d-%H-%M" ),
		}

		query = pystache.render(
			query_template,
			query_template_data
		)

		# Query for project execution logs
		logit( "Performing Athena query..." )
		query_results = TaskSpawner._perform_athena_query(
			aws_client_factory,
			credentials,
			query,
			True
		)

		logit( "Processing Athena results..." )

		# Format query results
		for query_result in query_results:
			# For the front-end
			query_result[ "log_id" ] = query_result[ "id" ]
			query_result[ "timestamp" ] = int( query_result[ "timestamp" ] )
			del query_result[ "id" ]

			# Generate a log path from the available data
			# example: PROJECT_ID/dt=DATE_SHARD/EXECUTION_PIPELINE_ID/TYPE~NAME~LOG_ID~TIMESTAMP

			log_file_path = project_id + "/dt=" + query_result[ "dt" ]
			log_file_path += "/" + execution_pipeline_id + "/"
			log_file_path += query_result[ "type" ] + "~"
			log_file_path += query_result[ "function_name" ] + "~"
			log_file_path += query_result[ "log_id" ] + "~"
			log_file_path += str( query_result[ "timestamp" ] )

			query_result[ "s3_key" ] = log_file_path

			del query_result[ "dt" ]

		logit( "Athena results have been processed.")

		return query_results

	@staticmethod
	def _execution_log_query_results_to_pipeline_id_dict( query_results ):
		"""
		This is the final format we return from the input query
		results (the list returned from Athena):

		{
			"{{execution_pipeline_id}}": {
				"SUCCESS": 0,
				"EXCEPTION": 2,
				"CAUGHT_EXCEPTION": 10,
				"block_executions": {
					"{{arn}}": {
						"SUCCESS": 0,
						"EXCEPTION": 2,
						"CAUGHT_EXCEPTION": 10,
					}
				}
			}
		}
		"""
		execution_pipeline_id_dict = {}

		for query_result in query_results:
			# If this is the first execution ID we've encountered then set that key
			# up with the default object structure
			if not ( query_result[ "execution_pipeline_id" ] in execution_pipeline_id_dict ):
				execution_pipeline_id_dict[ query_result[ "execution_pipeline_id" ] ] = {
					"SUCCESS": 0,
					"EXCEPTION": 0,
					"CAUGHT_EXCEPTION": 0,
					"timestamp": int( query_result[ "timestamp" ] ),
					"block_executions": {}
				}

			# If the timestamp is more recent that what is in the
			# execution pipeline data then update the field with the value
			# This is because we'd sort that by time (most recent) on the front end
			execution_pipeline_timestamp = execution_pipeline_id_dict[ query_result[ "execution_pipeline_id" ] ][ "timestamp" ]
			if int( query_result[ "timestamp" ] ) > execution_pipeline_timestamp:
				execution_pipeline_timestamp = int( query_result[ "timestamp" ] )

			# If this is the first ARN we've seen for this execution ID we'll set it up
			# with the default object template as well.
			block_executions = execution_pipeline_id_dict[ query_result[ "execution_pipeline_id" ] ][ "block_executions" ]
			if not ( query_result[ "arn" ] in block_executions ):
				block_executions[ query_result[ "arn" ] ] = {
					"SUCCESS": 0,
					"EXCEPTION": 0,
					"CAUGHT_EXCEPTION": 0
				}

			# Convert execution count to integer
			execution_int_count = int( query_result[ "count" ] )

			# Add execution count to execution ID totals
			execution_pipeline_id_dict[ query_result[ "execution_pipeline_id" ] ][ query_result[ "type" ]  ] += execution_int_count

			# Add execution count to ARN execution totals
			block_executions[ query_result[ "arn" ] ][ query_result[ "type" ] ] += execution_int_count

		return execution_pipeline_id_dict

	@run_on_executor
	@emit_runtime_metrics( "get_project_execution_logs" )
	def get_project_execution_logs( self, credentials, project_id, oldest_timestamp ):
		return TaskSpawner._get_project_execution_logs(
			self.aws_client_factory,
			credentials,
			project_id,
			oldest_timestamp
		)

	@staticmethod
	def _get_project_execution_logs( aws_client_factory, credentials, project_id, oldest_timestamp ):
		timestamp_datetime = datetime.datetime.fromtimestamp( oldest_timestamp )
		project_id = re.sub( REGEX_WHITELISTS[ "project_id" ], "", project_id )

		query_template = """
		SELECT arn, type, execution_pipeline_id, timestamp, dt, COUNT(*) as count
		FROM "refinery"."{{{project_id_table_name}}}"
		WHERE dt >= '{{{oldest_timestamp}}}'
		GROUP BY arn, type, execution_pipeline_id, timestamp, dt ORDER BY timestamp LIMIT 100000
		"""

		query_template_data = {
			"project_id_table_name": "PRJ_" + project_id.replace( "-", "_" ),
			"oldest_timestamp": timestamp_datetime.strftime( "%Y-%m-%d-%H-%M" )
		}

		query = pystache.render(
			query_template,
			query_template_data
		)

		# Query for project execution logs
		query_results = TaskSpawner._perform_athena_query(
			aws_client_factory,
			credentials,
			query,
			True
		)

		# Convert the Athena query results into an execution pipeline ID with the
		# results sorted into a dictionary with the key being the execution pipeline ID
		# and the value being an object with information about the total executions for
		# the execution pipeline ID and the block ARN execution totals contained within
		# that execution pipeline.
		execution_pipeline_id_dict = TaskSpawner._execution_log_query_results_to_pipeline_id_dict(
			query_results
		)

		return TaskSpawner._execution_pipeline_id_dict_to_frontend_format(
			execution_pipeline_id_dict
		)

	@staticmethod
	def _execution_pipeline_id_dict_to_frontend_format( execution_pipeline_id_dict ):

		final_return_format = []

		# Now convert it into the usable front-end format
		for execution_pipeline_id, aggregate_data in execution_pipeline_id_dict.iteritems():
			block_executions = []

			for block_arn, execution_status_counts in aggregate_data[ "block_executions" ].iteritems():
				block_executions.append({
					"arn": block_arn,
					"SUCCESS": execution_status_counts[ "SUCCESS" ],
					"CAUGHT_EXCEPTION": execution_status_counts[ "CAUGHT_EXCEPTION" ],
					"EXCEPTION": execution_status_counts[ "EXCEPTION" ],
				})

			final_return_format.append({
				"execution_pipeline_id": execution_pipeline_id,
				"block_executions": block_executions,
				"execution_pipeline_totals": {
					"SUCCESS": aggregate_data[ "SUCCESS" ],
					"CAUGHT_EXCEPTION": aggregate_data[ "CAUGHT_EXCEPTION" ],
					"EXCEPTION": aggregate_data[ "EXCEPTION" ],
				},
				"timestamp": aggregate_data[ "timestamp" ]
			})

		return final_return_format

	@run_on_executor
	@emit_runtime_metrics( "create_project_id_log_table" )
	def create_project_id_log_table( self, credentials, project_id ):
		return TaskSpawner._create_project_id_log_table(
			self.aws_client_factory,
			credentials,
			project_id
		)

	@staticmethod
	def _create_project_id_log_table( aws_client_factory, credentials, project_id ):
		project_id = re.sub( REGEX_WHITELISTS[ "project_id" ], "", project_id )
		table_name = "PRJ_" + project_id.replace( "-", "_" )

		# We set case sensitivity (because of nested JSON) and to ignore malformed JSON (just in case)
		query_template = """
		CREATE EXTERNAL TABLE IF NOT EXISTS refinery.{{REPLACE_ME_PROJECT_TABLE_NAME}} (
			`arn` string,
			`aws_region` string,
			`aws_request_id` string,
			`function_name` string,
			`function_version` string,
			`group_name` string,
			`id` string,
			`initialization_time` int,
			`invoked_function_arn` string,
			`memory_limit_in_mb` int,
			`name` string,
			`project_id` string,
			`stream_name` string,
			`timestamp` int,
			`type` string,
			`program_output` string,
			`input_data` string,
			`backpack` string,
			`return_data` string,
			`execution_pipeline_id` string
		)
		PARTITIONED BY (dt string)
		ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
		WITH SERDEPROPERTIES (
			'serialization.format' = '1',
			'ignore.malformed.json' = 'true',
			'case.insensitive' = 'false'
		) LOCATION 's3://refinery-lambda-logging-{{S3_BUCKET_SUFFIX}}/{{REPLACE_ME_PROJECT_ID}}/'
		TBLPROPERTIES ('has_encrypted_data'='false');
		"""

		# Replace with the formatted Athena table name
		query = query_template.replace(
			"{{REPLACE_ME_PROJECT_TABLE_NAME}}",
			table_name
		)

		# Replace with the actually project UUID
		query = query.replace(
			"{{REPLACE_ME_PROJECT_ID}}",
			project_id
		)

		# Replace the S3 bucket name with the actual
		# bucket
		query = query.replace(
			"{{S3_BUCKET_SUFFIX}}",
			credentials[ "s3_bucket_suffix" ]
		)

		# Perform the table creation query
		query_results = TaskSpawner._perform_athena_query(
			aws_client_factory,
			credentials,
			query,
			False
		)

	@run_on_executor
	@emit_runtime_metrics( "perform_athena_query" )
	def perform_athena_query( self, credentials, query, return_results ):
		return TaskSpawner._perform_athena_query(
			self.aws_client_factory,
			credentials,
			query,
			return_results
		)

	@staticmethod
	def _perform_athena_query( aws_client_factory, credentials, query, return_results ):
		athena_client = aws_client_factory.get_aws_client(
			"athena",
			credentials,
		)

		output_base_path = "s3://refinery-lambda-logging-" + credentials[ "s3_bucket_suffix" ] + "/athena/"

		# Start the query
		query_start_response = athena_client.start_query_execution(
			QueryString=query,
			QueryExecutionContext={
				"Database": "refinery"
			},
			ResultConfiguration={
				"OutputLocation": output_base_path,
				"EncryptionConfiguration": {
					"EncryptionOption": "SSE_S3"
				}
			},
			WorkGroup="refinery_workgroup"
		)

		# Ensure we have an execution ID to follow
		if not ( "QueryExecutionId" in query_start_response ):
			logit( query_start_response )
			raise Exception( "No query execution ID in response!" )

		query_execution_id = query_start_response[ "QueryExecutionId" ]

		QUERY_FAILED_STATES = [
			"CANCELLED",
			"FAILED"
		]

		query_status_results = {}

		# Max amount of times we'll attempt to query the execution
		# status. If the counter hits zero we break out.
		max_counter = 60

		# Poll for query status
		# For loops which do not have a discreet conditional break, we enforce
		# an upper bound of iterations.
		MAX_LOOP_ITERATIONS = 10000

		# Bound this loop to only execute MAX_LOOP_ITERATION times since we
		# cannot guarantee that the condition `continuation_token == False`
		# will ever be true.
		for _ in xrange(MAX_LOOP_ITERATIONS):
			# Check the status of the query
			query_status_result = athena_client.get_query_execution(
				QueryExecutionId=query_execution_id
			)

			query_execution_results = {}
			query_execution_status = "RUNNING"

			if "QueryExecution" in query_status_result:
				query_execution_status = query_status_result[ "QueryExecution" ][ "Status" ][ "State" ]

			if query_execution_status in QUERY_FAILED_STATES:
				logit( query_status_result )
				raise Exception( "Athena query failed!" )

			if query_execution_status == "SUCCEEDED":
				break

			time.sleep(1)

			# Decrement counter
			max_counter = max_counter - 1

			if max_counter <= 0:
				break

		s3_object_location = query_status_result[ "QueryExecution" ][ "ResultConfiguration" ][ "OutputLocation" ]

		# Sometimes we don't care about the result
		# In those cases we just return the S3 path in case the caller
		# Wants to grab the results themselves later
		if not return_results:
			return s3_object_location

		# Get S3 bucket and path from the s3 location string
		# s3://refinery-lambda-logging-uoits4nibdlslbq97qhfyb6ngkvzyewf/athena/
		s3_path = s3_object_location.replace(
			"s3://refinery-lambda-logging-" + credentials[ "s3_bucket_suffix" ],
			""
		)

		return TaskSpawner._get_athena_results_from_s3(
			aws_client_factory,
			credentials,
			"refinery-lambda-logging-" + credentials[ "s3_bucket_suffix" ],
			s3_path
		)

	@run_on_executor
	@emit_runtime_metrics( "get_athena_results_from_s3" )
	def get_athena_results_from_s3( self, credentials, s3_bucket, s3_path ):
		return TaskSpawner._get_athena_results_from_s3(
			self.aws_client_factory,
			credentials,
			s3_bucket,
			s3_path
		)

	@staticmethod
	def _get_athena_results_from_s3( aws_client_factory, credentials, s3_bucket, s3_path ):
		csv_data = TaskSpawner._read_from_s3(
			aws_client_factory,
			credentials,
			s3_bucket,
			s3_path
		)

		csv_handler = StringIO( csv_data )
		csv_reader = csv.DictReader(
			csv_handler,
			delimiter=",",
			quotechar='"'
		)

		return_array = []

		for row in csv_reader:
			return_array.append(
				row
			)

		return return_array

	@staticmethod
	def _create_aws_org_sub_account( app_config, aws_organization_client, refinery_aws_account_id, email ):
		account_name = "Refinery Customer Account " + refinery_aws_account_id

		response = aws_organization_client.create_account(
			Email=email,
			RoleName=app_config.get( "customer_aws_admin_assume_role" ),
			AccountName=account_name,
			IamUserAccessToBilling="DENY"
		)
		account_status_data = response[ "CreateAccountStatus" ]
		create_account_id = account_status_data[ "Id" ]

		# Loop while the account is being created (up to ~5 minutes)
		for _ in xrange(60):
			if account_status_data[ "State" ] == "SUCCEEDED" and "AccountId" in account_status_data:
				return {
					"account_name": account_name,
					"account_id": account_status_data[ "AccountId" ],
				}

			if account_status_data[ "State" ] == "FAILED":
				logit( "The account creation has failed!", "error" )
				logit( "Full account creation response is the following: ", "error" )
				logit( account_status_data )
				return False

			logit( "Current AWS account creation status is '" + account_status_data[ "State" ] + "', waiting 5 seconds before checking again..." )
			time.sleep( 5 )

			# Poll AWS again to see if the account creation has progressed
			response = aws_organization_client.describe_create_account_status(
				CreateAccountRequestId=create_account_id
			)
			account_status_data = response[ "CreateAccountStatus" ]

	@run_on_executor
	@emit_runtime_metrics( "get_assume_role_credentials" )
	def get_assume_role_credentials( self, aws_account_id, session_lifetime ):
		return TaskSpawner._get_assume_role_credentials(
			self.app_config,
			self.sts_client,
			aws_account_id,
			session_lifetime
		)

	@staticmethod
	def _get_assume_role_credentials( app_config, sts_client, aws_account_id, session_lifetime ):
		# Generate ARN for the sub-account AWS administrator role
		sub_account_admin_role_arn = "arn:aws:iam::" + str( aws_account_id ) + ":role/" + app_config.get( "customer_aws_admin_assume_role" )

		# Session lifetime must be a minimum of 15 minutes
		# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html#STS.Client.assume_role
		min_session_lifetime_seconds = 900
		if session_lifetime < min_session_lifetime_seconds:
			session_lifetime = min_session_lifetime_seconds

		role_session_name = "Refinery-Managed-Account-Support-" + get_urand_password( 12 )

		response = sts_client.assume_role(
			RoleArn=sub_account_admin_role_arn,
			RoleSessionName=role_session_name,
			DurationSeconds=session_lifetime
		)

		return {
			"access_key_id": response[ "Credentials" ][ "AccessKeyId" ],
			"secret_access_key": response[ "Credentials" ][ "SecretAccessKey" ],
			"session_token": response[ "Credentials" ][ "SessionToken" ],
			"expiration_date": response[ "Credentials" ][ "Expiration" ],
			"assumed_role_id": response[ "AssumedRoleUser" ][ "AssumedRoleId" ],
			"role_session_name": role_session_name,
			"arn": response[ "AssumedRoleUser" ][ "Arn" ],
		}

	@staticmethod
	def _create_new_console_user( app_config, access_key_id, secret_access_key, session_token, username, password ):
		# Create a Boto3 session with the assumed role credentials
		# This allows us to create a client which will be authenticated
		# as the account we assumed the role of.
		iam_session = boto3.Session(
			aws_access_key_id=access_key_id,
			aws_secret_access_key=secret_access_key,
			aws_session_token=session_token
		)

		# IAM client spawned from the assumed role session
		iam_client = iam_session.client( "iam" )

		# Create an IAM user
		create_user_response = iam_client.create_user(
			UserName=username
		)

		# Create IAM policy for the user
		create_policy_response = iam_client.create_policy(
			PolicyName="RefineryCustomerPolicy",
			PolicyDocument=json.dumps( app_config.get( "CUSTOMER_IAM_POLICY" ) ),
			Description="Refinery Labs managed AWS customer account policy."
		)

		# Attaches limited access policy to the AWS account to scope
		# down the permissions the Refinery customer can perform in
		# the AWS console.
		attach_policy_response = iam_client.attach_user_policy(
			UserName=username,
			PolicyArn=create_policy_response[ "Policy" ][ "Arn" ]
		)

		# Allow the IAM user to access the account through the console
		create_login_profile_response = iam_client.create_login_profile(
			UserName=username,
			Password=password,
			PasswordResetRequired=False,
		)

		return {
			"username": username,
			"password": password,
			"arn": create_user_response[ "User" ][ "Arn" ]
		}

	@run_on_executor
	@emit_runtime_metrics( "create_new_sub_aws_account" )
	def create_new_sub_aws_account( self, account_type, aws_account_id ):
		return TaskSpawner._create_new_sub_aws_account(
			self.app_config,
			self.db_session_maker,
			self.aws_organization_client,
			self.sts_client,
			account_type,
			aws_account_id
		)

	@staticmethod
	def _create_new_sub_aws_account( app_config, db_session_maker, aws_organization_client, sts_client, account_type, aws_account_id ):
		# Create a unique ID for the Refinery AWS account
		aws_unique_account_id = get_urand_password( 16 ).lower()

		# Store the AWS account in the database
		new_aws_account = AWSAccount()
		new_aws_account.account_label = ""
		new_aws_account.region = app_config.get( "region_name" )
		new_aws_account.s3_bucket_suffix = str( get_urand_password( 32 ) ).lower()
		new_aws_account.iam_admin_username = "refinery-customer"
		new_aws_account.iam_admin_password = get_urand_password( 32 )
		new_aws_account.redis_hostname = ""
		new_aws_account.redis_password = get_urand_password( 64 )
		new_aws_account.redis_port = 6379
		new_aws_account.redis_secret_prefix = get_urand_password( 40 )
		new_aws_account.terraform_state = ""
		new_aws_account.ssh_public_key = ""
		new_aws_account.ssh_private_key = ""
		new_aws_account.aws_account_email = app_config.get( "customer_aws_email_prefix" ) + aws_unique_account_id + app_config.get( "customer_aws_email_suffix" )
		new_aws_account.terraform_state_versions = []
		new_aws_account.aws_account_status = "CREATED"
		new_aws_account.account_type = account_type

		# Create AWS sub-account
		logit( "Creating AWS sub-account '" + str( new_aws_account.aws_account_email ) + "'..." )

		# Only create a sub-account if this is a MANAGED AWS account and skip
		# this step if we're onboarding a THIRDPARTY AWS account (e.g. self-hosted)
		if account_type == "MANAGED":
			# Create sub-AWS account
			account_creation_response = TaskSpawner._create_aws_org_sub_account(
				app_config,
				aws_organization_client,
				aws_unique_account_id,
				str( new_aws_account.aws_account_email ),
			)

			if account_creation_response == False:
				raise Exception( "Account creation failed, quitting out!" )

			new_aws_account.account_id = account_creation_response[ "account_id" ]
			logit( "Sub-account created! AWS account ID is " + new_aws_account.account_id + "." )
		elif account_type == "THIRDPARTY":
			new_aws_account.account_id = aws_account_id
			logit( "Using provided AWS Account ID " + new_aws_account.account_id + "." )

		assumed_role_credentials = {}

		# Try to assume the role up to 10 times
		for _ in xrange(10):
			logit( "Attempting to assume the sub-account's administrator role..." )

			try:
				# We then assume the administrator role for the sub-account we created
				assumed_role_credentials = TaskSpawner._get_assume_role_credentials(
					app_config,
					sts_client,
					str( new_aws_account.account_id ),
					3600 # One hour - TODO CHANGEME
				)
				break
			except botocore.exceptions.ClientError as boto_error:
				logit( "Assume role boto error:" + repr( boto_error ), "error" )
				# If it's not an AccessDenied exception it's not what we except so we re-raise
				if boto_error.response[ "Error" ][ "Code" ] != "AccessDenied":
					logit( "Unexpected Boto3 response: " + boto_error.response[ "Error" ][ "Code" ] )
					logit( boto_error.response )
					raise boto_error

				# Otherwise it's what we accept and we just need to wait.
				logit( "Got an Access Denied error, role is likely not propogated yet. Trying again in 5 seconds..." )
				time.sleep( 5 )

		logit( "Successfully assumed the sub-account's administrator role." )
		logit( "Minting a new AWS Console User account for the customer to use..." )

		# Using the credentials from the assumed role we mint an IAM console
		# user for Refinery customers to use to log into their managed AWS account.
		create_console_user_results = TaskSpawner._create_new_console_user(
			app_config,
			assumed_role_credentials[ "access_key_id" ],
			assumed_role_credentials[ "secret_access_key" ],
			assumed_role_credentials[ "session_token" ],
			str( new_aws_account.iam_admin_username ),
			str( new_aws_account.iam_admin_password )
		)

		# Add AWS account to database
		dbsession = db_session_maker()
		dbsession.add( new_aws_account )
		dbsession.commit()
		dbsession.close()

		logit( "New AWS account created successfully and stored in database as 'CREATED'!" )

		return True

	@run_on_executor
	@emit_runtime_metrics( "terraform_configure_aws_account" )
	def terraform_configure_aws_account( self, aws_account_dict ):
		return TaskSpawner._terraform_configure_aws_account(
			self.aws_client_factory,
			self.app_config,
			self.preterraform_manager,
			self.sts_client,
			aws_account_dict
		)

	@run_on_executor
	@emit_runtime_metrics( "write_terraform_base_files" )
	def write_terraform_base_files( self, aws_account_dict ):
		return TaskSpawner._write_terraform_base_files(
			self.app_config,
			self.sts_client,
			aws_account_dict
		)

	@staticmethod
	def _write_terraform_base_files( app_config, sts_client, aws_account_dict ):
		# Create a temporary working directory for the work.
		# Even if there's some exception thrown during the process
		# we will still delete the underlying state.
		temporary_dir = "/tmp/" + str( uuid.uuid4() ) + "/"

		result = False

		terraform_configuration_data = {}

		try:
			# Recursively copy files to the directory
			shutil.copytree(
				"/work/install/",
				temporary_dir
			)

			terraform_configuration_data = TaskSpawner.__write_terraform_base_files(
				app_config,
				sts_client,
				aws_account_dict,
				temporary_dir
			)
		except Exception as e:
			logit( "An exception occurred while writing terraform base files for AWS account ID " + aws_account_dict[ "account_id" ] )
			logit( e )

			# Delete the temporary directory reguardless.
			shutil.rmtree( temporary_dir )

			raise

		return terraform_configuration_data

	@staticmethod
	def __write_terraform_base_files( app_config, sts_client, aws_account_data, base_dir ):
		logit( "Setting up the base Terraform files (AWS Acc. ID '" + aws_account_data[ "account_id" ] + "')..." )

		# Get some temporary assume role credentials for the account
		assumed_role_credentials = TaskSpawner._get_assume_role_credentials(
			app_config,
			sts_client,
			str( aws_account_data[ "account_id" ] ),
			3600 # One hour - TODO CHANGEME
		)

		sub_account_admin_role_arn = "arn:aws:iam::" + str( aws_account_data[ "account_id" ] ) + ":role/" + app_config.get( "customer_aws_admin_assume_role" )

		# Write out the terraform configuration data
		terraform_configuration_data = {
			"session_token": assumed_role_credentials[ "session_token" ],
			"role_session_name": assumed_role_credentials[ "role_session_name" ],
			"assume_role_arn": sub_account_admin_role_arn,
			"access_key": assumed_role_credentials[ "access_key_id" ],
			"secret_key": assumed_role_credentials[ "secret_access_key" ],
			"region": app_config.get( "region_name" ),
			"s3_bucket_suffix": aws_account_data[ "s3_bucket_suffix" ],
			"redis_secrets": {
				"password": aws_account_data[ "redis_password" ],
				"secret_prefix": aws_account_data[ "redis_secret_prefix" ],
			}
		}

		logit( "Writing Terraform input variables to file..." )

		# Write configuration data to a file for Terraform to use.
		with open( base_dir + "customer_config.json", "w" ) as file_handler:
			file_handler.write(
				json.dumps(
					terraform_configuration_data
				)
			)

		# Write the latest terraform state to terraform.tfstate
		# If we have any state at all.
		if aws_account_data[ "terraform_state" ] != "":
			# First we write the current version to the database as a version to keep track

			terraform_state_file_path = base_dir + "terraform.tfstate"

			logit( "A previous terraform state file exists! Writing it to '" + terraform_state_file_path + "'..." )

			with open( terraform_state_file_path, "w" ) as file_handler:
				file_handler.write(
					aws_account_data[ "terraform_state" ]
				)

		logit( "The base terraform files have been created successfully at " + base_dir )

		terraform_configuration_data[ "base_dir" ] = base_dir

		return terraform_configuration_data

	@run_on_executor
	@emit_runtime_metrics( "terraform_apply" )
	def terraform_apply( self, aws_account_data, refresh_terraform_state=True ):
		"""
		This applies the latest terraform config to an account.

		THIS IS DANGEROUS, MAKE SURE YOU DID A FLEET TERRAFORM PLAN
		FIRST. NO EXCUSES, THIS IS ONE OF THE FEW WAYS TO BREAK PROD
		FOR OUR CUSTOMERS.

		-mandatory

		:param: refresh_terraform_state This value tells Terraform if it should refresh the state before running plan
		"""
		return TaskSpawner._terraform_apply(
			self.aws_client_factory,
			self.app_config,
			self.preterraform_manager,
			self.sts_client,
			aws_account_data,
			refresh_terraform_state
		)

	@staticmethod
	def _terraform_apply( aws_client_factory, app_config, preterraform_manager, sts_client, aws_account_data, refresh_terraform_state ):
		logit( "Ensuring existence of ECS service-linked role before continuing with terraform apply..." )
		preterraform_manager._ensure_ecs_service_linked_role_exists(
			aws_client_factory,
			aws_account_data
		)

		# The return data
		return_data = {
			"success": True,
			"stdout": "",
			"stderr": "",
			"original_tfstate": str(
				copy.copy(
					aws_account_data[ "terraform_state" ]
				)
			),
			"new_tfstate": "",
		}

		terraform_configuration_data = TaskSpawner._write_terraform_base_files(
			app_config,
			sts_client,
			aws_account_data
		)
		temporary_directory = terraform_configuration_data[ "base_dir" ]

		try:
			logit( "Performing 'terraform apply' to AWS Account " + aws_account_data[ "account_id" ] + "..." )

			refresh_state_parameter = "true" if refresh_terraform_state else "false"

			# Terraform plan
			process_handler = subprocess.Popen(
				[
					temporary_directory + "terraform",
					"apply",
					"-refresh=" + refresh_state_parameter,
					"-auto-approve",
					"-var-file",
					temporary_directory + "customer_config.json",
					],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False,
				universal_newlines=True,
				cwd=temporary_directory,
			)
			process_stdout, process_stderr = process_handler.communicate()
			return_data[ "stdout" ] = process_stdout
			return_data[ "stderr" ] = process_stderr

			# Pull the latest terraform state and return it
			# We need to do this regardless of if an error occurred.
			with open( temporary_directory + "terraform.tfstate", "r" ) as file_handler:
				return_data[ "new_tfstate" ] = file_handler.read()

			if process_stderr.strip() != "":
				logit( "The 'terraform apply' has failed!", "error" )
				logit( process_stderr, "error" )
				logit( process_stdout, "error" )

				# Alert us of the provisioning error so we can response to it
				TaskSpawner._send_terraform_provisioning_error(
					app_config,
					aws_account_data[ "account_id" ],
					str( process_stderr )
				)

				return_data[ "success" ] = False
		finally:
			# Ensure we clear the temporary directory no matter what
			shutil.rmtree( temporary_directory )

		logit( "'terraform apply' completed, returning results..." )

		return return_data

	@run_on_executor
	@emit_runtime_metrics( "terraform_plan" )
	def terraform_plan( self, aws_account_data, refresh_terraform_state=True ):
		"""
		This does a terraform plan to an account and sends an email
		with the results. This allows us to see the impact of a new
		terraform change before we roll it out across our customer's
		AWS accounts.
		:param: refresh_terraform_state This value tells Terraform if it should refresh the state before running plan
		"""
		return TaskSpawner._terraform_plan(
			self.app_config,
			self.sts_client,
			aws_account_data,
			refresh_terraform_state
		)

	@staticmethod
	def _terraform_plan( app_config, sts_client, aws_account_data, refresh_terraform_state ):
		terraform_configuration_data = TaskSpawner._write_terraform_base_files(
			app_config,
			sts_client,
			aws_account_data
		)
		temporary_directory = terraform_configuration_data[ "base_dir" ]

		try:
			logit( "Performing 'terraform plan' to AWS account " + aws_account_data[ "account_id" ] + "..." )

			refresh_state_parameter = "true" if refresh_terraform_state else "false"

			# Terraform plan
			process_handler = subprocess.Popen(
				[
					temporary_directory + "terraform",
					"plan",
					"-refresh=" + refresh_state_parameter,
					"-var-file",
					temporary_directory + "customer_config.json",
					],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False,
				universal_newlines=True,
				cwd=temporary_directory,
			)
			process_stdout, process_stderr = process_handler.communicate()

			if process_stderr.strip() != "":
				logit( "The 'terraform plan' has failed!", "error" )
				logit( process_stderr, "error" )
				logit( process_stdout, "error" )

				raise Exception( "Terraform plan failed." )
		finally:
			# Ensure we clear the temporary directory no matter what
			shutil.rmtree( temporary_directory )

		logit( "Terraform plan completed successfully, returning output." )
		return process_stdout

	@staticmethod
	def _terraform_configure_aws_account( aws_client_factory, app_config, preterraform_manager, sts_client, aws_account_data ):
		logit( "Ensuring existence of ECS service-linked role before continuing with AWS account configuration..." )
		preterraform_manager._ensure_ecs_service_linked_role_exists(
			aws_client_factory,
			aws_account_data
		)

		terraform_configuration_data = TaskSpawner._write_terraform_base_files(
			app_config,
			sts_client,
			aws_account_data
		)
		base_dir = terraform_configuration_data[ "base_dir" ]

		try:
			logit( "Setting up AWS account with terraform (AWS Acc. ID '" + aws_account_data[ "account_id" ] + "')..." )

			# Terraform apply
			process_handler = subprocess.Popen(
				[
					base_dir + "terraform",
					"apply",
					"-auto-approve",
					"-var-file",
					base_dir + "customer_config.json",
					],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False,
				universal_newlines=True,
				cwd=base_dir,
			)
			process_stdout, process_stderr = process_handler.communicate()

			if process_stderr.strip() != "":
				logit( "The Terraform provisioning has failed!", "error" )
				logit( process_stderr, "error" )
				logit( process_stdout, "error" )

				# Alert us of the provisioning error so we can get ahead of
				# it with AWS support.
				TaskSpawner._send_terraform_provisioning_error(
					app_config,
					aws_account_data[ "account_id" ],
					str( process_stderr )
				)

				raise Exception( "Terraform provisioning failed, AWS account marked as \"CORRUPT\"" )

			logit( "Running 'terraform output' to pull the account details..." )

			# Print Terraform output as JSON so we can read it.
			process_handler = subprocess.Popen(
				[
					base_dir + "terraform",
					"output",
					"-json"
				],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False,
				universal_newlines=True,
				cwd=base_dir,
			)
			process_stdout, process_stderr = process_handler.communicate()

			# Parse Terraform JSON output
			terraform_provisioned_account_details = json.loads(
				process_stdout
			)

			logit( "Pulled Terraform output successfully." )

			# Pull the terraform state and pull it so we can later
			# make terraform changes to user accounts.
			terraform_state = ""
			with open( base_dir + "terraform.tfstate", "r" ) as file_handler:
				terraform_state = file_handler.read()

			terraform_configuration_data[ "terraform_state" ] = terraform_state
			terraform_configuration_data[ "redis_hostname" ] = terraform_provisioned_account_details[ "redis_elastic_ip" ][ "value" ]
			terraform_configuration_data[ "ssh_public_key" ] = terraform_provisioned_account_details[ "refinery_redis_ssh_key_public_key_openssh" ][ "value" ]
			terraform_configuration_data[ "ssh_private_key" ] = terraform_provisioned_account_details[ "refinery_redis_ssh_key_private_key_pem" ][ "value" ]
		finally:
			# Ensure we clear the temporary directory no matter what
			shutil.rmtree( base_dir )

		return terraform_configuration_data

	@run_on_executor
	@emit_runtime_metrics( "unfreeze_aws_account" )
	def unfreeze_aws_account( self, credentials ):
		return TaskSpawner._unfreeze_aws_account(
			self.aws_client_factory,
			credentials
		)

	@staticmethod
	def _unfreeze_aws_account( aws_client_factory, credentials ):
		"""
		Unfreezes a previously-frozen AWS account, this is for situations
		where a user has gone over their free-trial or billing limit leading
		to their account getting frozen. By calling this the account will be
		re-enabled for regular Refinery use.
		* De-throttle all AWS Lambdas
		* Turn on EC2 instances (redis)
		"""
		logit( "Unfreezing AWS account..." )

		lambda_client = aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)

		ec2_client = aws_client_factory.get_aws_client(
			"ec2",
			credentials
		)

		# Pull all Lambda ARN(s)
		lambda_arns = TaskSpawner._get_lambda_arns(
			aws_client_factory,
			credentials
		)

		# Remove function throttle from each Lambda
		for lambda_arn in lambda_arns:
			lambda_client.delete_function_concurrency(
				FunctionName=lambda_arn
			)

		# Start EC2 instance(s)
		ec2_instance_ids = TaskSpawner._get_ec2_instance_ids( aws_client_factory, credentials )

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

		return True

	@staticmethod
	def _get_lambda_arns( aws_client_factory, credentials ):
		lambda_client = aws_client_factory.get_aws_client(
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

		# Don't list more than 200 pages of Lambdas (I hope this is never happens!)
		for _ in xrange(200):
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

		# Iterate over list of Lambda ARNs and set concurrency to zero for all
		for lambda_arn in lambda_arn_list:
			lambda_client.put_function_concurrency(
				FunctionName=lambda_arn,
				ReservedConcurrentExecutions=0
			)

		return lambda_arn_list

	@staticmethod
	def _get_ec2_instance_ids( aws_client_factory, credentials ):
		ec2_client = aws_client_factory.get_aws_client(
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

	@run_on_executor
	@emit_runtime_metrics( "freeze_aws_account" )
	def freeze_aws_account( self, credentials ):
		return TaskSpawner._freeze_aws_account( self.app_config, self.aws_client_factory, self.db_session_maker, credentials )

	@staticmethod
	def _freeze_aws_account( app_config, aws_client_factory, db_session_maker, credentials ):
		"""
		Freezes an AWS sub-account when the user has gone past
		their free trial or when they have gone tardy on their bill.

		This is different from closing an AWS sub-account in that it preserves
		the underlying resources in the account. Generally this is the
		"warning shot" before we later close the account and delete it all.

		The steps are as follows:
		* Disable AWS console access by changing the password
		* Revoke all active AWS console sessions - TODO
		* Iterate over all deployed Lambdas and throttle them
		* Stop all active CodeBuilds
		* Turn-off EC2 instances (redis)
		"""
		logit( "Freezing AWS account..." )

		iam_client = aws_client_factory.get_aws_client(
			"iam",
			credentials
		)

		lambda_client = aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)

		codebuild_client = aws_client_factory.get_aws_client(
			"codebuild",
			credentials
		)

		ec2_client = aws_client_factory.get_aws_client(
			"ec2",
			credentials
		)

		# Rotate and log out users from the AWS console
		new_console_user_password = TaskSpawner._recreate_aws_console_account(
			app_config,
			aws_client_factory,
			credentials,
			True
		)

		# Update the console login in the database
		dbsession = db_session_maker()
		aws_account = dbsession.query( AWSAccount ).filter_by(
			account_id=credentials[ "account_id" ]
		).first()
		aws_account.iam_admin_password = new_console_user_password
		dbsession.commit()

		# Get Lambda ARNs
		lambda_arn_list = TaskSpawner._get_lambda_arns( aws_client_factory, credentials )

		# List all CodeBuild builds and stop any that are running
		codebuild_build_ids = []
		codebuild_list_params = {}

		# Bound this loop to only execute MAX_LOOP_ITERATION times
		for _ in xrange(1000):
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

		ec2_instance_ids = TaskSpawner._get_ec2_instance_ids( aws_client_factory, credentials )

		stop_instance_response = ec2_client.stop_instances(
			InstanceIds=ec2_instance_ids
		)

		dbsession.close()
		return False

	@run_on_executor
	@emit_runtime_metrics( "recreate_aws_console_account" )
	def recreate_aws_console_account( self, credentials, rotate_password, force_continue=False ):
		return TaskSpawner._recreate_aws_console_account(
			self.app_config,
			self.aws_client_factory,
			credentials,
			rotate_password,
			force_continue=force_continue
		)

	@staticmethod
	def _recreate_aws_console_account( app_config, aws_client_factory, credentials, rotate_password, force_continue=False ):
		iam_client = aws_client_factory.get_aws_client(
			"iam",
			credentials
		)

		# The only way to revoke an AWS Console user's session
		# is to delete the console user and create a new one.

		# Generate the IAM policy ARN
		iam_policy_arn = "arn:aws:iam::" + credentials[ "account_id" ] + ":policy/RefineryCustomerPolicy"

		logit( "Deleting AWS console user..." )

		# TODO check responses from these calls?

		try:
			# Delete the current AWS console user
			delete_user_profile_response = iam_client.delete_login_profile(
				UserName=credentials[ "iam_admin_username" ],
			)

			# Remove the policy from the user
			detach_user_policy = iam_client.detach_user_policy(
				UserName=credentials[ "iam_admin_username" ],
				PolicyArn=iam_policy_arn
			)

			# Delete the IAM user
			delete_user_response = iam_client.delete_user(
				UserName=credentials[ "iam_admin_username" ],
			)
		except Exception as e:
			logit( "Unable to delete IAM user during recreate process" )

			# Raise the exception again unless the flag is set to force continuation
			if force_continue is False:
				raise e

		logit( "Re-creating the AWS console user..." )

		# Create the IAM user again
		delete_user_response = iam_client.create_user(
			UserName=credentials[ "iam_admin_username" ],
		)

		# Create the IAM user again
		delete_policy_response = iam_client.delete_policy(
			PolicyArn=iam_policy_arn
		)

		# Create IAM policy for the user
		create_policy_response = iam_client.create_policy(
			PolicyName="RefineryCustomerPolicy",
			PolicyDocument=json.dumps( app_config.get( "CUSTOMER_IAM_POLICY" ) ),
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
	@emit_runtime_metrics( "send_email" )
	def send_email( self, to_email_string, subject_string, message_text_string, message_html_string ):
		"""
		to_email_string: "example@refinery.io"
		subject_string: "Your important email"
		message_text_string: "You have an important email here!"
		message_html_string: "<h1>ITS IMPORTANT AF!</h1>"
		"""
		return TaskSpawner._send_email(
			self.app_config,
			to_email_string,
			subject_string,
			message_text_string,
			message_html_string
		)

	@staticmethod
	def _send_email( app_config, to_email_string, subject_string, message_text_string, message_html_string ):
		logit( "Sending email to '" + to_email_string + "' with subject '" + subject_string + "'..." )

		requests_options = {
			"auth": ( "api", app_config.get( "mailgun_api_key" ) ),
			"data": {
				"from": app_config.get( "from_email" ),
				"h:Reply-To": "support@refinery.io",
				"to": [
					to_email_string
				],
				"subject": subject_string,
			}
		}

		if message_text_string:
			requests_options[ "data" ][ "text" ] = message_text_string

		if message_html_string:
			requests_options[ "data" ][ "html" ] = message_html_string

		response = requests.post(
			"https://api.mailgun.net/v3/mail.refinery.io/messages",
			**requests_options
		)

		return response.text

	@staticmethod
	def _send_terraform_provisioning_error( app_config, aws_account_id, error_output ):
		TaskSpawner._send_email(
			app_config,
			app_config.get( "alerts_email" ),
			"[AWS Account Provisioning Error] The Refinery AWS Account #" + aws_account_id + " Encountered a Fatal Error During Terraform Provisioning",
			pystache.render(
				app_config.get( "EMAIL_TEMPLATES" )[ "terraform_provisioning_error_alert" ],
				{
					"aws_account_id": aws_account_id,
					"error_output": error_output,
				}
			),
			False,
		)

	@staticmethod
	def _send_account_freeze_email( app_config, aws_account_id, amount_accumulated, organization_admin_email ):
		TaskSpawner._send_email(
			app_config,
			app_config.get( "alerts_email" ),
			"[Freeze Alert] The Refinery AWS Account #" + aws_account_id + " has been frozen for going over its account limit!",
			False,
			pystache.render(
				app_config.get( "EMAIL_TEMPLATES" )[ "account_frozen_alert" ],
				{
					"aws_account_id": aws_account_id,
					"free_trial_billing_limit": app_config.get( "free_trial_billing_limit" ),
					"amount_accumulated": amount_accumulated,
					"organization_admin_email": organization_admin_email,
				}
			),
		)

	@run_on_executor
	@emit_runtime_metrics( "send_registration_confirmation_email" )
	def send_registration_confirmation_email( self, email_address, auth_token ):
		registration_confirmation_link = self.app_config.get( "web_origin" ) + "/authentication/email/" + auth_token

		TaskSpawner._send_email(
			self.app_config,
			email_address,
			"Refinery.io - Confirm your Refinery registration",
			pystache.render(
				self.app_config.get( "EMAIL_TEMPLATES" )[ "registration_confirmation_text" ],
				{
					"registration_confirmation_link": registration_confirmation_link,
				}
			),
			pystache.render(
				self.app_config.get( "EMAIL_TEMPLATES" )[ "registration_confirmation" ],
				{
					"registration_confirmation_link": registration_confirmation_link,
				}
			),
		)

	@run_on_executor
	@emit_runtime_metrics( "send_internal_registration_confirmation_email" )
	def send_internal_registration_confirmation_email( self, customer_email_address, customer_name, customer_phone ):
		TaskSpawner._send_email(
			self.app_config,
			self.app_config.get( "internal_signup_notification_email" ),
			"Refinery User Signup, " + customer_email_address,
			pystache.render(
				self.app_config.get( "EMAIL_TEMPLATES" )[ "internal_registration_notification_text" ],
				{
					"customer_email_address": customer_email_address,
					"customer_name": customer_name,
					"customer_phone": customer_phone
				}
			),
			pystache.render(
				self.app_config.get( "EMAIL_TEMPLATES" )[ "internal_registration_notification" ],
				{
					"customer_email_address": customer_email_address,
					"customer_name": customer_name,
					"customer_phone": customer_phone
				}
			),
			)

	@run_on_executor
	@emit_runtime_metrics( "send_authentication_email" )
	def send_authentication_email( self, email_address, auth_token ):
		authentication_link = self.app_config.get( "web_origin" ) + "/authentication/email/" + auth_token

		TaskSpawner._send_email(
			self.app_config,
			email_address,
			"Refinery.io - Login by email confirmation",
			pystache.render(
				self.app_config.get( "EMAIL_TEMPLATES" )[ "authentication_email_text" ],
				{
					"email_authentication_link": authentication_link,
				}
			),
			pystache.render(
				self.app_config.get( "EMAIL_TEMPLATES" )[ "authentication_email" ],
				{
					"email_authentication_link": authentication_link,
				}
			),
		)

	@run_on_executor
	@emit_runtime_metrics( "stripe_create_customer" )
	def stripe_create_customer( self, email, name, phone_number, source_token, metadata_dict ):
		# Create a customer in Stripe
		customer = stripe.Customer.create(
			email=email,
			name=name,
			phone=phone_number,
			source=source_token,
			metadata=metadata_dict
		)

		return customer[ "id" ]

	@run_on_executor
	@emit_runtime_metrics( "associate_card_token_with_customer_account" )
	def associate_card_token_with_customer_account( self, stripe_customer_id, card_token ):
		# Add the card to the customer's account.
		new_card = stripe.Customer.create_source(
			stripe_customer_id,
			source=card_token
		)

		return new_card[ "id" ]

	@run_on_executor
	@emit_runtime_metrics( "get_account_cards" )
	def get_account_cards( self, stripe_customer_id ):
		return TaskSpawner._get_account_cards( stripe_customer_id )

	@staticmethod
	def _get_account_cards( stripe_customer_id ):
		# Pull all of the metadata for the cards the customer
		# has on file with Stripe
		cards = stripe.Customer.list_sources(
			stripe_customer_id,
			object="card",
			limit=100,
		)

		# Pull the user's default card and add that
		# metadata to the card
		customer_info = TaskSpawner._get_stripe_customer_information(
			stripe_customer_id
		)

		for card in cards:
			is_primary = False
			if card[ "id" ] == customer_info[ "default_source" ]:
				is_primary = True
			card[ "is_primary" ] = is_primary

		return cards[ "data" ]

	@run_on_executor
	@emit_runtime_metrics( "get_stripe_customer_information" )
	def get_stripe_customer_information( self, stripe_customer_id ):
		return TaskSpawner._get_stripe_customer_information( stripe_customer_id )

	@staticmethod
	def _get_stripe_customer_information( stripe_customer_id ):
		return stripe.Customer.retrieve(
			stripe_customer_id
		)

	@run_on_executor
	@emit_runtime_metrics( "set_stripe_customer_default_payment_source" )
	def set_stripe_customer_default_payment_source( self, stripe_customer_id, card_id ):
		customer_update_response = stripe.Customer.modify(
			stripe_customer_id,
			default_source=card_id,
		)

		logit( customer_update_response )

	@run_on_executor
	@emit_runtime_metrics( "delete_card_from_account" )
	def delete_card_from_account( self, stripe_customer_id, card_id ):
		# We first have to pull the customers information so we
		# can verify that they are not deleting their default
		# payment source from Stripe.
		customer_information = TaskSpawner._get_stripe_customer_information(
			stripe_customer_id
		)

		# Throw an exception if this is the default source for the user
		if customer_information[ "default_source" ] == card_id:
			raise CardIsPrimaryException()

		# Delete the card from STripe
		delete_response = stripe.Customer.delete_source(
			stripe_customer_id,
			card_id
		)

		return True

	@run_on_executor
	@emit_runtime_metrics( "generate_managed_accounts_invoices" )
	def generate_managed_accounts_invoices( self, start_date_string, end_date_string ):
		"""
		Bills ultimately belong to the organization but are paid by
		the ADMINS of the organization. So we generate the invoices and
		then send them to the admins on the account for payment.

		Note that this is purely for accounts which are "managed" meaning
		we own the billing of the sub-AWS accounts and we upcharge and
		bill the customer.
		"""
		# Pull a list of organizations to generate invoices for
		dbsession = self.db_session_maker()
		organizations = dbsession.query( Organization )

		organization_ids = []

		for organization in organizations:
			organization_dict = organization.to_dict()
			organization_ids.append(
				organization_dict[ "id" ]
			)

		dbsession.close()

		# List of invoices to send out at the end
		"""
		{
			# To send invoice emails
			"admin_stripe_id": "...",
			"aws_account_bills": [],
		}
		"""
		invoice_list = []

		# Setting for if Refinery should just finalize the invoices
		# or if manual approve/editing is enabled. One is more careful
		# than the others.
		finalize_invoices_enabled = json.loads(
			self.app_config.get( "stripe_finalize_invoices" )
		)

		# Iterate over each organization
		for organization_id in organization_ids:
			dbsession = self.db_session_maker()
			organization = dbsession.query( Organization ).filter_by(
				id=organization_id
			).first()

			organization_dict = organization.to_dict()

			# If the organization is disabled we just skip it
			if organization.disabled == True:
				continue

			# If the organization is billing exempt, we skip it
			if organization.billing_exempt == True:
				continue

			# Check if the organization billing admin has validated
			# their email address. If not it means they never finished
			# the signup process so we can skip them.
			if organization.billing_admin_user.email_verified == False:
				continue

			current_organization_invoice_data = {
				"admin_stripe_id": "...",
				"aws_account_bills": [],
			}

			# Pull the organization billing admin and send them
			# the invoice email so they can pay it.
			current_organization_invoice_data[ "admin_stripe_id" ] = organization.billing_admin_user.payment_id

			# Get AWS accounts from organization
			organization_aws_accounts = []
			for aws_account in organization.aws_accounts:
				organization_aws_accounts.append(
					aws_account.to_dict()
				)
			dbsession.close()

			# Pull billing information for each AWS account
			for aws_account_dict in organization_aws_accounts:
				billing_information = TaskSpawner._get_sub_account_billing_data(
					self.app_config,
					self.db_session_maker,
					self.aws_cost_explorer,
					self.aws_client_factory,
					aws_account_dict[ "account_id" ],
					aws_account_dict[ "account_type" ],
					start_date_string,
					end_date_string,
					"monthly",
					False
				)

				current_organization_invoice_data[ "aws_account_bills" ].append({
					"aws_account_label": aws_account_dict[ "account_label" ],
					"aws_account_id": aws_account_dict[ "account_id" ],
					"billing_information": billing_information,
				})

			if "admin_stripe_id" in current_organization_invoice_data and current_organization_invoice_data[ "admin_stripe_id" ]:
				invoice_list.append(
					current_organization_invoice_data
				)

		for invoice_data in invoice_list:
			for aws_account_billing_data in invoice_data[ "aws_account_bills" ]:
				# We send one bill per managed AWS account if they have multiple

				for service_cost_data in aws_account_billing_data[ "billing_information" ][ "service_breakdown" ]:
					line_item_cents = int(
						float( service_cost_data[ "total" ] ) * 100
					)

					# If the item costs zero cents don't add it to the bill.
					if line_item_cents > 0:
						# Don't add "Managed" to the base-service fee.
						if "Fee" in service_cost_data[ "service_name" ]:
							service_description = service_cost_data[ "service_name" ]
						else:
							service_description = "Managed " + service_cost_data[ "service_name" ]

						if aws_account_billing_data[ "aws_account_label" ].strip() != "":
							service_description = service_description + " (Cloud Account: '" + aws_account_billing_data[ "aws_account_label" ] + "')"

						stripe.InvoiceItem.create(
							# Stripe bills in cents!
							amount=line_item_cents,
							currency=str( service_cost_data[ "unit" ] ).lower(),
							customer=invoice_data[ "admin_stripe_id" ],
							description=service_description,
						)

				invoice_creation_params = {
					"customer": invoice_data[ "admin_stripe_id" ],
					"auto_advance": True,
					"billing": "charge_automatically",
					"metadata": {
						"aws_account_id": aws_account_billing_data[ "aws_account_id" ]
					}
				}

				try:
					customer_invoice = stripe.Invoice.create(
						**invoice_creation_params
					)

					if finalize_invoices_enabled:
						customer_invoice.send_invoice()
				except Exception as e:
					logit( "Exception occurred while creating customer invoice, parameters were the following: " )
					logit( invoice_creation_params )
					logit( e )

		# Notify finance department that they have an hour to review the invoices
		return TaskSpawner._send_email(
			self.app_config,
			self.app_config.get( "billing_alert_email" ),
			"[URGENT][IMPORTANT]: Monthly customer invoice generation has completed. One hour to auto-finalization.",
			False,
			"The monthly Stripe invoice generation has completed. You have <b>one hour</b> to review invoices before they go out to customers.<br /><a href=\"https://dashboard.stripe.com/invoices\"><b>Click here to review the generated invoices</b></a><br /><br />",
		)

	@run_on_executor
	@emit_runtime_metrics( "pull_current_month_running_account_totals" )
	def pull_current_month_running_account_totals( self ):
		"""
		This runs through all of the sub-AWS accounts managed
		by Refinery and returns an array like the following:
		{
			"aws_account_id": "00000000000",
			"billing_total": "12.39",
			"unit": "USD",
		}
		"""
		date_info = get_current_month_start_and_end_date_strings()

		metric_name = "NetUnblendedCost"
		aws_account_running_cost_list = []

		ce_params = {
			"TimePeriod": {
				"Start": date_info[ "month_start_date" ],
				"End": date_info[ "next_month_first_day" ],
			},
			"Granularity": "MONTHLY",
			"Metrics": [
				metric_name
			],
			"GroupBy": [
				{
					"Type": "DIMENSION",
					"Key": "LINKED_ACCOUNT"
				}
			]
		}

		ce_response = {}

		# Bound this loop to only execute MAX_LOOP_ITERATION times
		for _ in xrange(1000):
			ce_response = self.aws_cost_explorer.get_cost_and_usage(
				**ce_params
			)
			account_billing_results = ce_response[ "ResultsByTime" ][0][ "Groups" ]

			for account_billing_result in account_billing_results:
				aws_account_running_cost_list.append({
					"aws_account_id": account_billing_result[ "Keys" ][0],
					"billing_total": account_billing_result[ "Metrics" ][ metric_name ][ "Amount" ],
					"unit": account_billing_result[ "Metrics" ][ metric_name ][ "Unit" ],
				})

			# Stop here if there are no more pages to iterate through.
			if ( "NextPageToken" in ce_response ) == False:
				break

			# If we have a next page token, then add it to our
			# parameters for the next paginated calls.
			ce_params[ "NextPageToken" ] = ce_response[ "NextPageToken" ]

		return aws_account_running_cost_list

	@run_on_executor
	@emit_runtime_metrics( "enforce_account_limits" )
	def enforce_account_limits( self, aws_account_running_cost_list ):
		"""
		{
			"aws_account_id": "00000000000",
			"billing_total": "12.39",
			"unit": "USD",
		}
		"""
		dbsession = self.db_session_maker()

		# Pull the configured free trial account limits
		free_trial_user_max_amount = float( self.app_config.get( "free_trial_billing_limit" ) )

		# Iterate over the input list and pull the related accounts
		for aws_account_info in aws_account_running_cost_list:
			# Pull relevant AWS account
			aws_account = dbsession.query( AWSAccount ).filter_by(
				account_id=aws_account_info[ "aws_account_id" ],
				aws_account_status="IN_USE",
			).first()

			# If there's no related AWS account in the database
			# we just skip over it because it's likely a non-customer
			# AWS account
			if aws_account is None:
				continue

			# Pull related organization
			owner_organization = dbsession.query( Organization ).filter_by(
				id=aws_account.organization_id
			).first()

			# Check if the user is a free trial user
			user_trial_info = get_user_free_trial_information( owner_organization.billing_admin_user )

			# If they are a free trial user, check if their usage has
			# exceeded the allowed limits
			exceeds_free_trial_limit = float( aws_account_info[ "billing_total" ] ) >= free_trial_user_max_amount
			if user_trial_info[ "is_using_trial" ] and exceeds_free_trial_limit:
				logit( "[ STATUS ] Enumerated user has exceeded their free trial.")
				logit( "[ STATUS ] Taking action against free-trial account..." )
				freeze_result = TaskSpawner._freeze_aws_account(
					self.app_config,
					self.aws_client_factory,
					self.db_session_maker,
					aws_account.to_dict()
				)

				# Send account frozen email to us to know that it happened
				TaskSpawner._send_account_freeze_email(
					self.app_config,
					aws_account_info[ "aws_account_id" ],
					aws_account_info[ "billing_total" ],
					owner_organization.billing_admin_user.email
				)

		dbsession.close()

	@run_on_executor
	@emit_runtime_metrics( "get_sub_account_month_billing_data" )
	def get_sub_account_month_billing_data( self, account_id, account_type, billing_month, use_cache ):
		# Parse the billing month into a datetime object
		billing_month_datetime = datetime.datetime.strptime(
			billing_month,
			"%Y-%m"
		)

		# Get first day of the month
		billing_start_date = billing_month_datetime.strftime( "%Y-%m-%d" )

		# Get the first day of the next month
		# This is some magic to ensure we end up on the next month since a month
		# never has 32 days.
		next_month_date = billing_month_datetime + datetime.timedelta( days=32 )
		billing_end_date = next_month_date.strftime( "%Y-%m-01" )

		return TaskSpawner._get_sub_account_billing_data(
			self.app_config,
			self.db_session_maker,
			self.aws_cost_explorer,
			self.aws_client_factory,
			account_id,
			account_type,
			billing_start_date,
			billing_end_date,
			"monthly",
			use_cache
		)

	@run_on_executor
	@emit_runtime_metrics( "mark_account_needs_closing" )
	def mark_account_needs_closing( self, email ):
		dbsession = self.db_session_maker()

		row = dbsession.query(User, Organization, AWSAccount).filter(
			User.organization_id == Organization.id
		).filter(
			Organization.id == AWSAccount.organization_id
		).filter(
			AWSAccount.aws_account_status == "IN_USE",
			AWSAccount.account_type == "MANAGED",
			User.email == email
		).first()

		if row is None:
			logit('unable to find user with email: ' + email)
			return False

		aws_account = row[2]
		aws_account.aws_account_status = "NEEDS_CLOSING"

		dbsession.commit()
		dbsession.close()
		return True

	@run_on_executor
	@emit_runtime_metrics( "do_account_cleanup" )
	def do_account_cleanup( self ):
		"""
		When an account has been closed on refinery, the AWS account associated with it has gone stale.
		In order to prevent any future charges of this account, we close it out using a script which:
		1) Resets the root AWS account password (required to do anything with the account)
		2) Waits for the mailgun API to receive the email
		3) Logs into the root AWS account
		4) Marks account to be closed
		"""
		delete_account_lambda_arn = self.app_config.get( "delete_account_lambda_arn" )

		dbsession = self.db_session_maker()

		# find all organizations which have been marked as 'disabled'
		rows = dbsession.query(User, Organization, AWSAccount).filter(
			User.organization_id == Organization.id
		).filter(
			Organization.id == AWSAccount.organization_id
		).filter(
			AWSAccount.aws_account_status == "NEEDS_CLOSING",
			AWSAccount.account_type == "MANAGED"
		).all()

		# load all of the results to be processed
		accounts = [
			(row[2].id, row[2].aws_account_email) for row in rows]
		dbsession.close()

		removed_accounts = 0
		for aws_account in accounts:
			account_id = aws_account[0]
			email = aws_account[1]

			response = self.aws_lambda_client.invoke(
				FunctionName=delete_account_lambda_arn,
				InvocationType="RequestResponse",
				LogType="Tail",
				Payload=json.dumps({
					"email": email
				})
			)

			if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
				logit("failed to remove account: " + email)
			else:
				# mark the account as closed
				dbsession = self.db_session_maker()
				account = dbsession.query(AWSAccount).filter(
					AWSAccount.id == account_id
				).first()
				account.aws_account_status = "CLOSED"
				dbsession.commit()
				dbsession.close()

				removed_accounts += 1

		return removed_accounts

	@staticmethod
	def _get_sub_account_billing_data( app_config, db_session_maker, aws_cost_explorer, aws_client_factory, account_id, account_type, start_date, end_date, granularity, use_cache ):
		"""
		Pull the service breakdown list and return it along with the totals.
		Note that this data is not marked up. This function does the work of marking it up.
		{
			"bill_total": {
				"total": "283.92",
				"unit": "USD"
			},
			"service_breakdown": [
				{
					"service_name": "AWS Cost Explorer",
					"total": "1.14",
					"unit": "USD"
				},
			...
		"""
		service_breakdown_list = TaskSpawner._get_sub_account_service_breakdown_list(
			app_config,
			db_session_maker,
			aws_cost_explorer,
			aws_client_factory,
			account_id,
			account_type,
			start_date,
			end_date,
			granularity,
			use_cache
		)

		return_data = {
			"bill_total": {
				"total": 0,
				"unit": "USD",
			},
			"service_breakdown": []
		}

		total_amount = 0.00

		# Remove some of the AWS branding from the billing
		remove_aws_branding_words = [
			"AWS",
			"Amazon",
		]

		# Keywords which remove the item from the billing line
		not_billed_words = [
			"Elastic Compute Cloud",
			"EC2"
		]

		markup_multiplier = 1 + ( int( app_config.get( "mark_up_percent" ) ) / 100 )

		# Markup multiplier
		if account_type == "THIRDPARTY":
			# For the self-hosted (THIRDPARTY) accounts the multiplier is just 1
			# this is because we normally double the AWS pricing and pay half to AWS.
			# In the THIRDPARTY situation, the customer pays AWS directly and we just
			# take our cut off the top.
			markup_multiplier = 1

		# Check if this is the first billing month
		is_first_account_billing_month = is_organization_first_month(
			db_session_maker,
			account_id
		)

		for service_breakdown_info in service_breakdown_list:
			# Remove branding words from service name
			service_name = service_breakdown_info[ "service_name" ]
			for aws_branding_word in remove_aws_branding_words:
				service_name = service_name.replace(
					aws_branding_word,
					""
				).strip()

			# If it's an AWS EC2-related billing item we strike it
			# because it's part of our $5 base fee
			should_be_ignored = False
			for not_billed_word in not_billed_words:
				if not_billed_word in service_name:
					should_be_ignored = True

			# If it matches our keywords we'll strike it from
			# the bill
			if should_be_ignored:
				continue

			# Mark up the total for the service
			service_total = float( service_breakdown_info[ "total" ] )

			# Don't add it as a line item if it's zero
			if service_total > 0:
				service_total = get_billing_rounded_float(
					service_total
				) * markup_multiplier

				return_data[ "service_breakdown" ].append({
					"service_name": service_name,
					"unit": service_breakdown_info[ "unit" ],
					"total": ( "%.2f" % service_total ),
				})

				total_amount = total_amount + service_total

		# This is where we upgrade the billing total if it's not at least $5/mo
		# $5/mo is our floor price.
		if total_amount < 5.00 and is_first_account_billing_month == False:
			amount_to_add = ( 5.00 - total_amount )
			return_data[ "service_breakdown" ].append({
				"service_name": "Floor Fee (Bills are minimum $5/month, see refinery.io/pricing for more information).",
				"unit": "usd",
				"total": ( "%.2f" % amount_to_add ),
			})
			total_amount = 5.00

		return_data[ "bill_total" ] = ( "%.2f" % total_amount )

		return return_data

	@staticmethod
	def _get_sub_account_service_breakdown_list( app_config, db_session_maker, aws_cost_explorer, aws_client_factory, account_id, account_type, start_date, end_date, granularity, use_cache ):
		"""
		Return format:

		[
			{
				"service_name": "EC2 - Other",
				"unit": "USD",
				"total": "10.0245523",
			}
			...
		]
		"""
		dbsession = db_session_maker()
		# Pull related AWS account and get the database ID for it
		aws_account = dbsession.query( AWSAccount ).filter_by(
			account_id=account_id,
		).first()

		# If the use_cache is enabled we'll check the database for an
		# already cached bill.
		# The oldest a cached bill can be is 24 hours, otherwise a new
		# one will be generated and cached. This allows our customers to
		# always have a daily service total if they want it.
		if use_cache:
			current_timestamp = int( time.time() )
			# Basically 24 hours before the current time.
			oldest_usable_cached_result_timestamp = current_timestamp - ( 60 * 60 * 24 )
			billing_collection = dbsession.query( CachedBillingCollection ).filter_by(
				billing_start_date=start_date,
				billing_end_date=end_date,
				billing_granularity=granularity,
				aws_account_id=aws_account.id
			).filter(
				CachedBillingCollection.timestamp >= oldest_usable_cached_result_timestamp
			).order_by(
				CachedBillingCollection.timestamp.desc()
			).first()

			# If billing collection exists format and return it
			if billing_collection:
				# Create a service breakdown list from database data
				service_breakdown_list = []

				for billing_item in billing_collection.billing_items:
					service_breakdown_list.append({
						"service_name": billing_item.service_name,
						"unit": billing_item.unit,
						"total": billing_item.total,
					})

				dbsession.close()
				return service_breakdown_list

		# Pull the raw billing data via the AWS CostExplorer API
		# Note that this returned data is not marked up.
		# This also costs us 1 cent each time we make this request
		# Which is why we implement caching for user billing.
		service_breakdown_list = TaskSpawner._api_get_sub_account_billing_data(
			app_config,
			db_session_maker,
			aws_cost_explorer,
			aws_client_factory,
			account_id,
			account_type,
			start_date,
			end_date,
			granularity,
		)

		# Since we've queried this data we'll cache it for future
		# retrievals.
		new_billing_collection = CachedBillingCollection()
		new_billing_collection.billing_start_date = start_date
		new_billing_collection.billing_end_date = end_date
		new_billing_collection.billing_granularity = granularity
		new_billing_collection.aws_account_id = aws_account.id

		# Add all of the line items as billing items
		for service_breakdown_data in service_breakdown_list:
			billing_item = CachedBillingItem()
			billing_item.service_name = service_breakdown_data[ "service_name" ]
			billing_item.unit = service_breakdown_data[ "unit" ]
			billing_item.total = service_breakdown_data[ "total" ]
			new_billing_collection.billing_items.append(
				billing_item
			)

		dbsession.add( new_billing_collection )
		dbsession.commit()
		dbsession.close()

		return service_breakdown_list

	@staticmethod
	def _api_get_sub_account_billing_data( app_config, db_session_maker, aws_cost_explorer, aws_client_factory, account_id, account_type, start_date, end_date, granularity ):
		"""
		account_id: 994344292413
		start_date: 2017-05-01
		end_date: 2017-06-01
		granularity: "daily" || "hourly" || "monthly"
		"""
		metric_name = "NetUnblendedCost"

		and_statements = [
			{
				"Not": {
					"Dimensions": {
						"Key": "RECORD_TYPE",
						"Values": [
							"Credit"
						]
					}
				}
			}
		]

		billing_client = None
		if account_type == "MANAGED":
			and_statements.append({
				"Dimensions": {
					"Key": "LINKED_ACCOUNT",
					"Values": [
						str( account_id )
					]
				}
			})
			billing_client = aws_cost_explorer
		elif account_type == "THIRDPARTY":
			# For third party we need to do an assume role into the account
			dbsession = db_session_maker()
			aws_account = dbsession.query( AWSAccount ).filter_by(
				account_id=account_id
			).first()
			aws_account_dict = aws_account.to_dict()
			dbsession.close()

			billing_client = aws_client_factory.get_aws_client(
				"ce",
				aws_account_dict
			)

			and_statements.append({
				"Tags": {
					"Key": "RefineryResource",
					"Values": [
						"true"
					]
				}
			})

		if billing_client is None:
			raise Exception("billing_client not set due to unhandled account type: {}".format(account_type))

		usage_parameters = {
			"TimePeriod": {
				"Start": start_date,
				"End": end_date,
			},
			"Filter": {
				"And": and_statements
			},
			"Granularity": granularity.upper(),
			"Metrics": [ metric_name ],
			"GroupBy": [
				{
					"Type": "DIMENSION",
					"Key": "SERVICE"
				}
			]
		}

		logit( "Parameters: " )
		logit( usage_parameters )

		try:
			response = billing_client.get_cost_and_usage(
				**usage_parameters
			)
		except ClientError as e:
			TaskSpawner._send_email(
				app_config,
				app_config.get( "alerts_email" ),
				"[Billing Notification] The Refinery AWS Account #" + account_id + " Encountered An Error When Calculating the Bill",
				"See HTML email.",
				pystache.render(
					app_config.get( "EMAIL_TEMPLATES" )[ "billing_error_email" ],
					{
						"account_id": account_id,
						"code": e.response[ "Error" ][ "Code" ],
						"message": e.response[ "Error" ][ "Message" ],
					}
				),
				)
			return []

		logit( "Cost and usage resonse: " )
		logit( response )

		cost_groups = response[ "ResultsByTime" ][0][ "Groups" ]

		service_breakdown_list = []

		for cost_group in cost_groups:
			cost_group_name = cost_group[ "Keys" ][0]
			unit = cost_group[ "Metrics" ][ metric_name ][ "Unit" ]
			total = cost_group[ "Metrics" ][ metric_name ][ "Amount" ]
			service_breakdown_list.append({
				"service_name": cost_group_name,
				"unit": unit,
				"total": total,
			})

		return service_breakdown_list

	@run_on_executor
	@emit_runtime_metrics( "get_sub_account_billing_forecast" )
	def get_sub_account_billing_forecast( self, account_id, start_date, end_date, granularity ):
		"""
		account_id: 994344292413
		start_date: 2017-05-01
		end_date: 2017-06-01
		granularity: monthly"
		"""
		metric_name = "NET_UNBLENDED_COST"

		# Markup multiplier
		markup_multiplier = 1 + ( int( self.app_config.get( "mark_up_percent" ) ) / 100 )

		forcecast_parameters = {
			"TimePeriod": {
				"Start": start_date,
				"End": end_date,
			},
			"Filter": {
				"Dimensions": {
					"Key": "LINKED_ACCOUNT",
					"Values": [
						str( account_id )
					]
				}
			},
			"Granularity": granularity.upper(),
			"Metric": metric_name
		}

		response = self.aws_cost_explorer.get_cost_forecast(
			**forcecast_parameters
		)

		forecast_total = float( response[ "Total" ][ "Amount" ] ) * markup_multiplier
		forecast_total_string = numpy.format_float_positional( forecast_total )
		forecast_unit = response[ "Total" ][ "Unit" ]

		return {
			"forecasted_total": forecast_total_string,
			"unit": forecast_unit
		}

	@run_on_executor
	@emit_runtime_metrics( "check_if_layer_exists" )
	def check_if_layer_exists( self, credentials, layer_name ):
		lambda_client = self.aws_client_factory.get_aws_client( "lambda", credentials )

		try:
			response = lambda_client.get_layer_version(
				LayerName=layer_name,
				VersionNumber=1
			)
		except ClientError as e:
			if e.response[ "Error" ][ "Code" ] == "ResourceNotFoundException":
				return False

		return True

	@run_on_executor
	@emit_runtime_metrics( "create_lambda_layer" )
	def create_lambda_layer( self, credentials, layer_name, description, s3_bucket, s3_object_key ):
		lambda_client = self.aws_client_factory.get_aws_client( "lambda", credentials )

		response = lambda_client.publish_layer_version(
			LayerName="RefineryManagedLayer_" + layer_name,
			Description=description,
			Content={
				"S3Bucket": s3_bucket,
				"S3Key": s3_object_key,
			},
			CompatibleRuntimes=[
				"python2.7",
				"provided",
			],
			LicenseInfo="See layer contents for license information."
		)

		return {
			"sha256": response[ "Content" ][ "CodeSha256" ],
			"size": response[ "Content" ][ "CodeSize" ],
			"version": response[ "Version" ],
			"layer_arn": response[ "LayerArn" ],
			"layer_version_arn": response[ "LayerVersionArn" ],
			"created_date": response[ "CreatedDate" ]
		}

	@run_on_executor
	@emit_runtime_metrics( "warm_up_lambda" )
	def warm_up_lambda( self, credentials, arn, warmup_concurrency_level ):
		lambda_client = self.aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)
		response = lambda_client.invoke(
			FunctionName=arn,
			InvocationType="Event",
			LogType="Tail",
			Payload=json.dumps({
				"_refinery": {
					"warmup": warmup_concurrency_level,
				}
			})
		)

	@run_on_executor
	@emit_runtime_metrics( "execute_aws_lambda" )
	def execute_aws_lambda( self, credentials, arn, input_data ):
		return TaskSpawner._execute_aws_lambda(
			self.aws_client_factory,
			credentials,
			arn,
			input_data
		)

	@staticmethod
	def _execute_aws_lambda( aws_client_factory, credentials, arn, input_data ):
		lambda_client = aws_client_factory.get_aws_client( "lambda", credentials )
		response = lambda_client.invoke(
			FunctionName=arn,
			InvocationType="RequestResponse",
			LogType="Tail",
			Payload=json.dumps(
				input_data
			)
		)

		full_response = response[ "Payload" ].read()

		# Decode it all the way
		try:
			full_response = json.loads(
				json.loads(
					full_response
				)
			)
		except:
			pass

		prettify_types = [
			dict,
			list
		]

		if type( full_response ) in prettify_types:
			full_response = json.dumps(
				full_response,
				indent=4
			)

		if type( full_response ) != str:
			full_response = str( full_response )

		# Detect from response if it was an error
		is_error = False

		if "FunctionError" in response:
			is_error = True

		log_output = base64.b64decode(
			response[ "LogResult" ]
		)

		# Strip the Lambda stuff from the output
		if "RequestId:" in log_output:
			log_lines = log_output.split( "\n" )
			returned_log_lines = []

			for log_line in log_lines:
				if log_line.startswith( "START RequestId: " ):
					continue

				if log_line.startswith( "END RequestId: " ):
					continue

				if log_line.startswith( "REPORT RequestId: " ):
					continue

				if log_line.startswith( "XRAY TraceId: " ):
					continue

				if "START RequestId: " in log_line:
					log_line = log_line.split( "START RequestId: " )[0]

				if "END RequestId: " in log_line:
					log_line = log_line.split( "END RequestId: " )[0]

				if "REPORT RequestId: " in log_line:
					log_line = log_line.split( "REPORT RequestId: " )[0]

				if "XRAY TraceId: " in log_line:
					log_line = log_line.split( "XRAY TraceId: " )[0]

				returned_log_lines.append(
					log_line
				)

			log_output = "\n".join( returned_log_lines )

		# Mark truncated if logs are not complete
		truncated = True
		if "START RequestId: " in log_output and "END RequestId: " in log_output:
			truncated = False

		return {
			"truncated": truncated,
			"arn": arn,
			"version": response[ "ExecutedVersion" ],
			"status_code": response[ "StatusCode" ],
			"logs": log_output,
			"is_error": is_error,
			"returned_data": full_response,
		}

	@run_on_executor
	@emit_runtime_metrics( "delete_aws_lambda" )
	def delete_aws_lambda( self, credentials, arn_or_name ):
		return TaskSpawner._delete_aws_lambda(
			self.aws_client_factory,
			credentials,
			arn_or_name
		)

	@staticmethod
	def _delete_aws_lambda( aws_client_factory, credentials, arn_or_name ):
		lambda_client = aws_client_factory.get_aws_client( "lambda", credentials )
		return lambda_client.delete_function(
			FunctionName=arn_or_name
		)

	@run_on_executor
	@emit_runtime_metrics( "update_lambda_environment_variables" )
	def update_lambda_environment_variables( self, credentials, func_name, environment_variables ):
		lambda_client = self.aws_client_factory.get_aws_client( "lambda", credentials )

		# Generate environment variables data structure
		env_data = {}
		for env_pair in environment_variables:
			env_data[ env_pair[ "key" ] ] = env_pair[ "value" ]

		response = lambda_client.update_function_configuration(
			FunctionName=func_name,
			Environment={
				"Variables": env_data
			},
		)

		return response

	@staticmethod
	def _build_lambda( app_config, aws_client_factory, credentials, lambda_object ):
		logit( "Building Lambda " + lambda_object.language + " with libraries: " + str( lambda_object.libraries ), "info" )
		if not ( lambda_object.language in LAMBDA_SUPPORTED_LANGUAGES ):
			raise Exception( "Error, this language '" + lambda_object.language + "' is not yet supported by refinery!" )

		if lambda_object.language == "python2.7":
			package_zip_data = TaskSpawner._build_python27_lambda(
				app_config,
				aws_client_factory,
				credentials,
				lambda_object.code,
				lambda_object.libraries
			)
		elif lambda_object.language == "python3.6":
			package_zip_data = TaskSpawner._build_python36_lambda(
				app_config,
				aws_client_factory,
				credentials,
				lambda_object.code,
				lambda_object.libraries
			)
		elif lambda_object.language == "php7.3":
			package_zip_data = TaskSpawner._build_php_73_lambda(
				app_config,
				aws_client_factory,
				credentials,
				lambda_object.code,
				lambda_object.libraries
			)
		elif lambda_object.language == "nodejs8.10":
			package_zip_data = TaskSpawner._build_nodejs_810_lambda(
				app_config,
				aws_client_factory,
				credentials,
				lambda_object.code,
				lambda_object.libraries
			)
		elif lambda_object.language == "nodejs10.16.3":
			package_zip_data = TaskSpawner._build_nodejs_10163_lambda(
				app_config,
				aws_client_factory,
				credentials,
				lambda_object.code,
				lambda_object.libraries
			)
		elif lambda_object.language == "go1.12":
			lambda_object.code = TaskSpawner._get_go_112_base_code(
				app_config,
				lambda_object.code
			)
			package_zip_data = BuilderManager._get_go112_zip(
				aws_client_factory,
				credentials,
				lambda_object
			)
		elif lambda_object.language == "ruby2.6.4":
			package_zip_data = TaskSpawner._build_ruby_264_lambda(
				app_config,
				aws_client_factory,
				credentials,
				lambda_object.code,
				lambda_object.libraries
			)
		else:
			raise InvalidLanguageException("Unknown language supplied to build Lambda with")

		# Add symlink if it's an inline execution
		if lambda_object.is_inline_execution:
			package_zip_data = add_shared_files_symlink_to_zip(
				package_zip_data
			)
		else:
			# If it's an inline execution we don't add the shared files folder because
			# we'll be live injecting them into /tmp/
			# Add shared files to Lambda package as well.
			package_zip_data = add_shared_files_to_zip(
				package_zip_data,
				lambda_object.shared_files_list
			)

		return package_zip_data

	@run_on_executor
	@emit_runtime_metrics( "set_lambda_reserved_concurrency" )
	def set_lambda_reserved_concurrency( self, credentials, arn, reserved_concurrency_count ):
		# Create Lambda client
		lambda_client = self.aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)

		set_concurrency_response = lambda_client.put_function_concurrency(
			FunctionName=arn,
			ReservedConcurrentExecutions=int( reserved_concurrency_count )
		)

	@run_on_executor
	@log_exception
	@emit_runtime_metrics( "deploy_aws_lambda" )
	def deploy_aws_lambda( self, credentials, lambda_object ):
		"""
		Here we do caching to see if we've done this exact build before
		(e.g. the same language, code, and libraries). If we have an the
		previous zip package is still in S3 we can just return that.

		The zip key is {{SHA256_OF_LANG-CODE-LIBRARIES}}.zip
		"""
		# Generate libraries object for now until we modify it to be a dict/object
		libraries_object = {}
		for library in lambda_object.libraries:
			libraries_object[ str( library ) ] = "latest"

		is_inline_execution_string = "-INLINE" if lambda_object.is_inline_execution else "-NOT_INLINE"

		# Generate SHA256 hash input for caching key
		hash_input = lambda_object.language + "-" + lambda_object.code + "-" + json.dumps(
			libraries_object,
			sort_keys=True
		) + json.dumps(
			lambda_object.shared_files_list
		) + is_inline_execution_string
		hash_key = hashlib.sha256(
			hash_input
		).hexdigest()
		s3_package_zip_path = hash_key + ".zip"

		# Check to see if it's in the S3 cache
		already_exists = False

		# Create S3 client
		s3_client = self.aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		# Check if we've already deployed this exact same Lambda before
		already_exists = TaskSpawner._s3_object_exists(
			self.aws_client_factory,
			credentials,
			credentials[ "lambda_packages_bucket" ],
			s3_package_zip_path
		)

		if not already_exists:
			# Build the Lambda package .zip and return the zip data for it
			lambda_zip_package_data = TaskSpawner._build_lambda(
				self.app_config,
				self.aws_client_factory,
				credentials,
				lambda_object
			)

			# Write it the cache
			s3_client.put_object(
				Key=s3_package_zip_path,
				Bucket=credentials[ "lambda_packages_bucket" ],
				Body=lambda_zip_package_data,
			)

		lambda_deploy_result = TaskSpawner._deploy_aws_lambda(
			self.aws_client_factory,
			credentials,
			lambda_object,
			s3_package_zip_path,
		)

		# If it's an inline execution we can cache the
		# built Lambda and re-used it for future executions
		# that share the same configuration when run.
		if lambda_object.is_inline_execution:
			logit( "Caching inline execution to speed up future runs..." )
			TaskSpawner._cache_inline_lambda_execution(
				self.aws_client_factory,
				self.db_session_maker,
				self.lambda_manager,
				credentials,
				lambda_object.language,
				lambda_object.max_execution_time,
				lambda_object.memory,
				lambda_object.environment_variables,
				lambda_object.layers,
				lambda_object.libraries,
				lambda_deploy_result[ "FunctionArn" ],
				lambda_deploy_result[ "CodeSize" ]
			)

		return lambda_deploy_result

	@staticmethod
	def _get_cached_inline_execution_lambda_entries( db_session_maker, credentials ):
		# Check how many inline execution Lambdas we already have
		# saved in AWS. If it's too many we need to clean up!
		# Get the oldest saved inline execution from the stack and
		# delete it from AWS. This way we don't fill up the 75GB
		# per-account limitation!
		dbsession = db_session_maker()
		existing_inline_execution_lambdas_objects = dbsession.query(
			InlineExecutionLambda
		).filter_by(
			aws_account_id=credentials[ "id" ]
		).order_by(
			InlineExecutionLambda.last_used_timestamp.asc()
		).all()

		existing_inline_execution_lambdas = []

		for existing_inline_execution_lambdas_object in existing_inline_execution_lambdas_objects:
			existing_inline_execution_lambdas.append(
				existing_inline_execution_lambdas_object.to_dict()
			)

		dbsession.close()

		logit(
			"Number of existing Lambdas cached for inline executions: " + str( len( existing_inline_execution_lambdas_objects ) )
		)

		return existing_inline_execution_lambdas

	@staticmethod
	def _delete_cached_inline_execution_lambda(
			aws_client_factory, db_session_maker, lambda_manager, credentials, arn, lambda_uuid ):
		# TODO: Call instance method not the static one
		# noinspection PyProtectedMember
		lambda_manager._delete_lambda(
			aws_client_factory,
			credentials,
			False,
			False,
			False,
			arn
		)

		# Delete the Lambda from the database now that we've
		# deleted it from AWS.
		dbsession = db_session_maker()
		dbsession.query( InlineExecutionLambda ).filter_by(
			id=lambda_uuid
		).delete()
		dbsession.commit()
		dbsession.close()

	@staticmethod
	def _add_inline_execution_lambda_entry( db_session_maker, credentials, inline_execution_hash_key, arn, lambda_size ):
		# Add Lambda to inline execution database so we know we can
		# re-use it at a later time.
		dbsession = db_session_maker()
		inline_execution_lambda = InlineExecutionLambda()
		inline_execution_lambda.unique_hash_key = inline_execution_hash_key
		inline_execution_lambda.arn = arn
		inline_execution_lambda.size = lambda_size
		inline_execution_lambda.aws_account_id = credentials[ "id" ]
		dbsession.add( inline_execution_lambda )
		dbsession.commit()
		dbsession.close()

	@staticmethod
	def _cache_inline_lambda_execution( aws_client_factory, db_session_maker, lambda_manager, credentials, language, timeout, memory, environment_variables, layers, libraries, arn, lambda_size ):
		inline_execution_hash_key = TaskSpawner._get_inline_lambda_hash_key(
			language,
			timeout,
			memory,
			environment_variables,
			layers,
			libraries
		)

		# Maximum amount of inline execution Lambdas to leave deployed
		# at a time in AWS. This is a tradeoff between speed and storage
		# amount consumed in AWS.
		max_number_of_inline_execution_lambdas = 20

		# Pull previous database entries for inline execution Lambdas we're caching
		existing_inline_execution_lambdas = TaskSpawner._get_cached_inline_execution_lambda_entries(
			db_session_maker,
			credentials
		)

		if existing_inline_execution_lambdas and len( existing_inline_execution_lambdas ) > max_number_of_inline_execution_lambdas:
			number_of_lambdas_to_delete = len( existing_inline_execution_lambdas ) - max_number_of_inline_execution_lambdas

			logit( "Deleting #" + str( number_of_lambdas_to_delete ) + " old cached inline execution Lambda(s) from AWS..." )

			lambdas_to_delete = existing_inline_execution_lambdas[:number_of_lambdas_to_delete]

			for lambda_to_delete in lambdas_to_delete:
				logit( "Deleting '" + lambda_to_delete[ "arn" ] + "' from AWS..." )

				TaskSpawner._delete_cached_inline_execution_lambda(
					aws_client_factory,
					db_session_maker,
					lambda_manager,
					credentials,
					lambda_to_delete[ "arn" ],
					lambda_to_delete[ "id" ]
				)

		TaskSpawner._add_inline_execution_lambda_entry(
			db_session_maker,
			credentials,
			inline_execution_hash_key,
			arn,
			lambda_size
		)

	@staticmethod
	def _get_inline_lambda_hash_key( language, timeout, memory, environment_variables, lambda_layers, libraries ):
		hash_dict = {
			"language": language,
			"timeout": timeout,
			"memory": memory,
			"environment_variables": environment_variables,
			"layers": lambda_layers
		}

		# For Go we don't include the libraries in the inline Lambda
		# hash key because the final binary is built in ECS before
		# being pulled down by the inline Lambda.
		if language != "go1.12":
			hash_dict[ "libraries" ] = libraries

		hash_key = hashlib.sha256(
			json.dumps(
				hash_dict,
				sort_keys=True
			)
		).hexdigest()

		return hash_key

	@staticmethod
	def _deploy_aws_lambda( aws_client_factory, credentials, lambda_object, s3_package_zip_path ):
		# Generate environment variables data structure
		env_data = {}
		for env_pair in lambda_object.environment_variables:
			env_data[ env_pair[ "key" ] ] = env_pair[ "value" ]

		# Create Lambda client
		lambda_client = aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)

		# Add pricing tag
		lambda_object.tags_dict = {
			"RefineryResource": "true"
		}

		try:
			# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.create_function
			response = lambda_client.create_function(
				FunctionName=lambda_object.name,
				Runtime="provided",
				Role=lambda_object.role,
				Handler="lambda._init",
				Code={
					"S3Bucket": credentials[ "lambda_packages_bucket" ],
					"S3Key": s3_package_zip_path,
				},
				Description="A Lambda deployed by refinery",
				Timeout=int(lambda_object.max_execution_time),
				MemorySize=int(lambda_object.memory),
				Publish=True,
				VpcConfig=lambda_object.vpc_data,
				Environment={
					"Variables": env_data
				},
				Tags=lambda_object.tags_dict,
				Layers=lambda_object.layers,
			)
		except ClientError as e:
			if e.response[ "Error" ][ "Code" ] == "ResourceConflictException":
				# Delete the existing lambda
				delete_response = TaskSpawner._delete_aws_lambda(
					aws_client_factory,
					credentials,
					lambda_object.name
				)

				# Now create it since we're clear
				# TODO: THIS IS A POTENTIAL INFINITE LOOP!
				return TaskSpawner._deploy_aws_lambda(
					aws_client_factory,
					credentials,
					lambda_object,
					s3_package_zip_path
				)
			raise

		return response

	@run_on_executor
	@emit_runtime_metrics( "get_final_zip_package_path" )
	def get_final_zip_package_path( self, language, libraries ):
		return TaskSpawner._get_final_zip_package_path( language, libraries )

	@staticmethod
	def _get_final_zip_package_path( language, libraries_object ):
		hash_input = language + "-" + json.dumps( libraries_object, sort_keys=True )
		hash_key = hashlib.sha256(
			hash_input
		).hexdigest()
		final_s3_package_zip_path = hash_key + ".zip"
		return final_s3_package_zip_path

	@staticmethod
	def _get_python36_lambda_base_zip( aws_client_factory, credentials, libraries ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		libraries_object = {}
		for library in libraries:
			libraries_object[ str( library ) ] = "latest"

		final_s3_package_zip_path = TaskSpawner._get_final_zip_package_path(
			"python3.6",
			libraries_object
		)

		object_exists = TaskSpawner._s3_object_exists(
			aws_client_factory,
			credentials,
			credentials[ "lambda_packages_bucket" ],
			final_s3_package_zip_path
		)

		if object_exists:
			return TaskSpawner._read_from_s3(
				aws_client_factory,
				credentials,
				credentials[ "lambda_packages_bucket" ],
				final_s3_package_zip_path
			)

		# Kick off CodeBuild for the libraries to get a zip artifact of
		# all of the libraries.
		build_id = TaskSpawner._start_python36_codebuild(
			aws_client_factory,
			credentials,
			libraries_object
		)

		# This continually polls for the CodeBuild build to finish
		# Once it does it returns the raw artifact zip data.
		return TaskSpawner._get_codebuild_artifact_zip_data(
			aws_client_factory,
			credentials,
			build_id,
			final_s3_package_zip_path
		)

	@staticmethod
	def _get_python27_lambda_base_zip( aws_client_factory, credentials, libraries ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		libraries_object = {}
		for library in libraries:
			libraries_object[ str( library ) ] = "latest"

		final_s3_package_zip_path = TaskSpawner._get_final_zip_package_path(
			"python2.7",
			libraries_object
		)

		object_exists = TaskSpawner._s3_object_exists(
			aws_client_factory,
			credentials,
			credentials[ "lambda_packages_bucket" ],
			final_s3_package_zip_path
		)

		if object_exists:
			return TaskSpawner._read_from_s3(
				aws_client_factory,
				credentials,
				credentials[ "lambda_packages_bucket" ],
				final_s3_package_zip_path
			)

		# Kick off CodeBuild for the libraries to get a zip artifact of
		# all of the libraries.
		build_id = TaskSpawner._start_python27_codebuild(
			aws_client_factory,
			credentials,
			libraries_object
		)

		# This continually polls for the CodeBuild build to finish
		# Once it does it returns the raw artifact zip data.
		return TaskSpawner._get_codebuild_artifact_zip_data(
			aws_client_factory,
			credentials,
			build_id,
			final_s3_package_zip_path
		)

	@run_on_executor
	@emit_runtime_metrics( "start_python36_codebuild" )
	def start_python36_codebuild( self, credentials, libraries_object ):
		return TaskSpawner._start_python36_codebuild(
			self.aws_client_factory,
			credentials,
			libraries_object
		)

	@staticmethod
	def _start_python36_codebuild( aws_client_factory, credentials, libraries_object ):
		"""
		Returns a build ID to be polled at a later time
		"""
		codebuild_client = aws_client_factory.get_aws_client(
			"codebuild",
			credentials
		)

		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		requirements_text = ""
		for key, value in libraries_object.iteritems():
			if value != "latest":
				requirements_text += key + "==" + value + "\n"
			else:
				requirements_text += key + "\n"

		# Create empty zip file
		codebuild_zip = io.BytesIO( EMPTY_ZIP_DATA )

		buildspec_template = {
			"artifacts": {
				"files": [
					"**/*"
				]
			},
			"phases": {
				"build": {
					"commands": [
						"pip install --target . -r requirements.txt"
					]
				},
			},
			"run-as": "root",
			"version": 0.1
		}

		with zipfile.ZipFile( codebuild_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			# Write buildspec.yml defining the build process
			buildspec = zipfile.ZipInfo(
				"buildspec.yml"
			)
			buildspec.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				buildspec,
				yaml.dump(
					buildspec_template
				)
			)

			# Write the package.json
			requirements_txt_file = zipfile.ZipInfo(
				"requirements.txt"
			)
			requirements_txt_file.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				requirements_txt_file,
				requirements_text
			)

		codebuild_zip_data = codebuild_zip.getvalue()
		codebuild_zip.close()

		# S3 object key of the build package, randomly generated.
		s3_key = "buildspecs/" + str( uuid.uuid4() ) + ".zip"

		# Write the CodeBuild build package to S3
		s3_response = s3_client.put_object(
			Bucket=credentials[ "lambda_packages_bucket" ],
			Body=codebuild_zip_data,
			Key=s3_key,
			ACL="public-read", # THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
		)

		# Fire-off the build
		codebuild_response = codebuild_client.start_build(
			projectName="refinery-builds",
			sourceTypeOverride="S3",
			imageOverride="docker.io/python:3.6.9",
			sourceLocationOverride=credentials[ "lambda_packages_bucket" ] + "/" + s3_key,
		)

		build_id = codebuild_response[ "build" ][ "id" ]
		return build_id

	@run_on_executor
	@emit_runtime_metrics( "start_python27_codebuild" )
	def start_python27_codebuild( self, credentials, libraries_object ):
		return TaskSpawner._start_python27_codebuild(
			self.aws_client_factory,
			credentials,
			libraries_object
		)

	@staticmethod
	def _start_python27_codebuild( aws_client_factory, credentials, libraries_object ):
		"""
		Returns a build ID to be polled at a later time
		"""
		codebuild_client = aws_client_factory.get_aws_client(
			"codebuild",
			credentials
		)

		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		requirements_text = ""
		for key, value in libraries_object.iteritems():
			if value != "latest":
				requirements_text += key + "==" + value + "\n"
			else:
				requirements_text += key + "\n"

		# Create empty zip file
		codebuild_zip = io.BytesIO( EMPTY_ZIP_DATA )

		buildspec_template = {
			"artifacts": {
				"files": [
					"**/*"
				]
			},
			"phases": {
				"build": {
					"commands": [
						"pip install --target . -r requirements.txt"
					]
				},
			},
			"run-as": "root",
			"version": 0.1
		}

		with zipfile.ZipFile( codebuild_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			# Write buildspec.yml defining the build process
			buildspec = zipfile.ZipInfo(
				"buildspec.yml"
			)
			buildspec.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				buildspec,
				yaml.dump(
					buildspec_template
				)
			)

			# Write the package.json
			requirements_txt_file = zipfile.ZipInfo(
				"requirements.txt"
			)
			requirements_txt_file.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				requirements_txt_file,
				requirements_text
			)

		codebuild_zip_data = codebuild_zip.getvalue()
		codebuild_zip.close()

		# S3 object key of the build package, randomly generated.
		s3_key = "buildspecs/" + str( uuid.uuid4() ) + ".zip"

		# Write the CodeBuild build package to S3
		s3_response = s3_client.put_object(
			Bucket=credentials[ "lambda_packages_bucket" ],
			Body=codebuild_zip_data,
			Key=s3_key,
			ACL="public-read", # THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
		)

		# Fire-off the build
		codebuild_response = codebuild_client.start_build(
			projectName="refinery-builds",
			sourceTypeOverride="S3",
			imageOverride="docker.io/python:2.7",
			sourceLocationOverride=credentials[ "lambda_packages_bucket" ] + "/" + s3_key,
		)

		build_id = codebuild_response[ "build" ][ "id" ]
		return build_id

	@run_on_executor
	@emit_runtime_metrics( "start_ruby264_codebuild" )
	def start_ruby264_codebuild( self, credentials, libraries_object ):
		return TaskSpawner._start_ruby264_codebuild(
			self.aws_client_factory,
			credentials,
			libraries_object
		)

	@staticmethod
	def _get_gemfile( libraries_object ):
		# Generate "Gemfile" with dependencies
		# Below specifies ruby 2.6.3 because that's what AWS's CodeBuild
		# has installed.
		gemfile = """source "https://rubygems.org"\n"""
		for key, value in libraries_object.iteritems():
			if value == "latest":
				gemfile += "gem '" + key + "'\n"
			else:
				gemfile += "gem '" + key + "', '" + value + "'\n"

		return gemfile

	@staticmethod
	def _start_ruby264_codebuild( aws_client_factory, credentials, libraries_object ):
		"""
		Returns a build ID to be polled at a later time
		"""
		codebuild_client = aws_client_factory.get_aws_client(
			"codebuild",
			credentials
		)

		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		# Create empty zip file
		codebuild_zip = io.BytesIO( EMPTY_ZIP_DATA )

		# Generate Gemfile
		gemfile = TaskSpawner._get_gemfile( libraries_object )

		buildspec_template = {
			"artifacts": {
				"files": [
					"**/*"
				]
			},
			"phases": {
				"build": {
					"commands": [
						"mkdir installed_gems/",
						"bundle install --path ./installed_gems/"
					]
				},
				"install": {
					"runtime-versions": {
						"ruby": 2.6
					}
				}
			},
			"version": 0.2
		}

		with zipfile.ZipFile( codebuild_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			# Write buildspec.yml defining the build process
			buildspec = zipfile.ZipInfo(
				"buildspec.yml"
			)
			buildspec.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				buildspec,
				yaml.dump(
					buildspec_template
				)
			)

			# Write the package.json
			gemfile_ref = zipfile.ZipInfo(
				"Gemfile"
			)
			gemfile_ref.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				gemfile_ref,
				gemfile
			)

		codebuild_zip_data = codebuild_zip.getvalue()
		codebuild_zip.close()

		# S3 object key of the build package, randomly generated.
		s3_key = "buildspecs/" + str( uuid.uuid4() ) + ".zip"

		# Write the CodeBuild build package to S3
		s3_response = s3_client.put_object(
			Bucket=credentials[ "lambda_packages_bucket" ],
			Body=codebuild_zip_data,
			Key=s3_key,
			ACL="public-read", # THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
		)

		# Fire-off the build
		codebuild_response = codebuild_client.start_build(
			projectName="refinery-builds",
			sourceTypeOverride="S3",
			sourceLocationOverride=credentials[ "lambda_packages_bucket" ] + "/" + s3_key,
		)

		build_id = codebuild_response[ "build" ][ "id" ]

		return build_id

	@run_on_executor
	@emit_runtime_metrics( "start_node810_codebuild" )
	def start_node810_codebuild( self, credentials, libraries_object ):
		return TaskSpawner._start_node810_codebuild(
			self.aws_client_factory,
			credentials,
			libraries_object
		)

	@staticmethod
	def _start_node810_codebuild( aws_client_factory, credentials, libraries_object ):
		"""
		Returns a build ID to be polled at a later time
		"""
		codebuild_client = aws_client_factory.get_aws_client(
			"codebuild",
			credentials
		)

		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		package_json_template = {
			"name": "refinery-lambda",
			"version": "1.0.0",
			"description": "Lambda created by Refinery",
			"main": "main.js",
			"dependencies": libraries_object,
			"devDependencies": {},
			"scripts": {}
		}

		# Create empty zip file
		codebuild_zip = io.BytesIO( EMPTY_ZIP_DATA )

		buildspec_template = {
			"artifacts": {
				"files": [
					"**/*"
				]
			},
			"phases": {
				"build": {
					"commands": [
						"npm install"
					]
				},
				"install": {
					"runtime-versions": {
						"nodejs": 8
					}
				}
			},
			"version": 0.2
		}

		with zipfile.ZipFile( codebuild_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			# Write buildspec.yml defining the build process
			buildspec = zipfile.ZipInfo(
				"buildspec.yml"
			)
			buildspec.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				buildspec,
				yaml.dump(
					buildspec_template
				)
			)

			# Write the package.json
			package_json = zipfile.ZipInfo(
				"package.json"
			)
			package_json.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				package_json,
				json.dumps(
					package_json_template
				)
			)

		codebuild_zip_data = codebuild_zip.getvalue()
		codebuild_zip.close()

		# S3 object key of the build package, randomly generated.
		s3_key = "buildspecs/" + str( uuid.uuid4() ) + ".zip"

		# Write the CodeBuild build package to S3
		s3_response = s3_client.put_object(
			Bucket=credentials[ "lambda_packages_bucket" ],
			Body=codebuild_zip_data,
			Key=s3_key,
			ACL="public-read", # THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
		)

		# Fire-off the build
		codebuild_response = codebuild_client.start_build(
			projectName="refinery-builds",
			sourceTypeOverride="S3",
			sourceLocationOverride=credentials[ "lambda_packages_bucket" ] + "/" + s3_key,
		)

		build_id = codebuild_response[ "build" ][ "id" ]

		return build_id

	@run_on_executor
	@emit_runtime_metrics( "s3_object_exists" )
	def s3_object_exists( self, credentials, bucket_name, object_key ):
		return TaskSpawner._s3_object_exists(
			self.aws_client_factory,
			credentials,
			bucket_name,
			object_key
		)

	@staticmethod
	def _s3_object_exists( aws_client_factory, credentials, bucket_name, object_key ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		already_exists = False
		try:
			s3_head_response = s3_client.head_object(
				Bucket=bucket_name,
				Key=object_key
			)

			# If we didn't encounter a not-found exception, it exists.
			already_exists = True
		except ClientError as e:
			pass

		return already_exists

	@staticmethod
	def _get_ruby_264_lambda_base_zip( aws_client_factory, credentials, libraries ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		libraries_object = {}
		for library in libraries:
			libraries_object[ str( library ) ] = "latest"

		final_s3_package_zip_path = TaskSpawner._get_final_zip_package_path(
			"ruby2.6.4",
			libraries_object
		)

		if TaskSpawner._s3_object_exists( aws_client_factory, credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
			return TaskSpawner._read_from_s3(
				aws_client_factory,
				credentials,
				credentials[ "lambda_packages_bucket" ],
				final_s3_package_zip_path
			)

		# Kick off CodeBuild for the libraries to get a zip artifact of
		# all of the libraries.
		build_id = TaskSpawner._start_ruby264_codebuild(
			aws_client_factory,
			credentials,
			libraries_object
		)

		# This continually polls for the CodeBuild build to finish
		# Once it does it returns the raw artifact zip data.
		return TaskSpawner._get_codebuild_artifact_zip_data(
			aws_client_factory,
			credentials,
			build_id,
			final_s3_package_zip_path
		)

	@staticmethod
	def _get_nodejs_810_lambda_base_zip( aws_client_factory, credentials, libraries ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		libraries_object = {}
		for library in libraries:
			libraries_object[ str( library ) ] = "latest"

		final_s3_package_zip_path = TaskSpawner._get_final_zip_package_path(
			"nodejs8.10",
			libraries_object
		)

		if TaskSpawner._s3_object_exists( aws_client_factory, credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
			return TaskSpawner._read_from_s3(
				aws_client_factory,
				credentials,
				credentials[ "lambda_packages_bucket" ],
				final_s3_package_zip_path
			)

		# Kick off CodeBuild for the libraries to get a zip artifact of
		# all of the libraries.
		build_id = TaskSpawner._start_node810_codebuild(
			aws_client_factory,
			credentials,
			libraries_object
		)

		# This continually polls for the CodeBuild build to finish
		# Once it does it returns the raw artifact zip data.
		return TaskSpawner._get_codebuild_artifact_zip_data(
			aws_client_factory,
			credentials,
			build_id,
			final_s3_package_zip_path
		)

	@run_on_executor
	@emit_runtime_metrics( "get_codebuild_artifact_zip_data" )
	def get_codebuild_artifact_zip_data( self, credentials, build_id, final_s3_package_zip_path ):
		return TaskSpawner._get_codebuild_artifact_zip_data(
			self.aws_client_factory,
			credentials,
			build_id,
			final_s3_package_zip_path
		)

	@staticmethod
	def _get_codebuild_artifact_zip_data( aws_client_factory, credentials, build_id, final_s3_package_zip_path ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		# Wait until the codebuild is finished
		# This is pieced out so that we can also kick off codebuilds
		# without having to pull the final zip result
		TaskSpawner._finalize_codebuild(
			aws_client_factory,
			credentials,
			build_id,
			final_s3_package_zip_path
		)

		return TaskSpawner._read_from_s3(
			aws_client_factory,
			credentials,
			credentials[ "lambda_packages_bucket" ],
			final_s3_package_zip_path
		)

	@run_on_executor
	@emit_runtime_metrics( "finalize_codebuild" )
	def finalize_codebuild( self, credentials, build_id, final_s3_package_zip_path ):
		return TaskSpawner._finalize_codebuild(
			self.aws_client_factory,
			credentials,
			build_id,
			final_s3_package_zip_path
		)

	@staticmethod
	def _finalize_codebuild( aws_client_factory, credentials, build_id, final_s3_package_zip_path ):
		codebuild_client = aws_client_factory.get_aws_client(
			"codebuild",
			credentials
		)

		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		build_info = {}

		# Generate output artifact location from the build ID
		build_id_parts = build_id.split( ":" )
		output_artifact_path = build_id_parts[1] + "/package.zip"

		# Loop until we have the build information (up to ~2 minutes)
		for _ in xrange(50):
			# Check the status of the build we just kicked off
			codebuild_build_status_response = codebuild_client.batch_get_builds(
				ids=[
					build_id
				]
			)
			build_info = codebuild_build_status_response[ "builds" ][0]
			build_status = build_info[ "buildStatus" ]

			if build_status != "IN_PROGRESS":
				break

			logit( "Build ID " + build_id + " is still in progress, querying the status again in 2 seconds...")
			time.sleep( 2 )

		if build_status != "SUCCEEDED":
			# Pull log group
			log_group_name = build_info[ "logs" ][ "groupName" ]

			# Pull stream name
			log_stream_name = build_info[ "logs" ][ "streamName" ]

			log_output = TaskSpawner._get_lambda_cloudwatch_logs(
				aws_client_factory,
				credentials,
				log_group_name,
				log_stream_name
			)

			msg = "Build ID " + build_id + " failed with status code '" + build_status + "'!"
			raise BuildException(msg, log_output)

		# We now copy this artifact to a location with a deterministic hash name
		# so that we can query for its existence and cache previously-build packages.
		s3_copy_response = s3_client.copy_object(
			Bucket=credentials[ "lambda_packages_bucket" ],
			CopySource={
				"Bucket": credentials[ "lambda_packages_bucket" ],
				"Key": output_artifact_path
			},
			Key=final_s3_package_zip_path
		)

		return True

	@staticmethod
	def _get_php73_lambda_base_zip( aws_client_factory, credentials, libraries ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		libraries_object = {}
		for library in libraries:
			libraries_object[ str( library ) ] = "latest"

		final_s3_package_zip_path = TaskSpawner._get_final_zip_package_path(
			"php7.3",
			libraries_object
		)

		if TaskSpawner._s3_object_exists( aws_client_factory, credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
			return TaskSpawner._read_from_s3(
				aws_client_factory,
				credentials,
				credentials[ "lambda_packages_bucket" ],
				final_s3_package_zip_path
			)

		# Kick off CodeBuild for the libraries to get a zip artifact of
		# all of the libraries.
		build_id = TaskSpawner._start_php73_codebuild(
			aws_client_factory,
			credentials,
			libraries_object
		)

		# This continually polls for the CodeBuild build to finish
		# Once it does it returns the raw artifact zip data.
		return TaskSpawner._get_codebuild_artifact_zip_data(
			aws_client_factory,
			credentials,
			build_id,
			final_s3_package_zip_path
		)

	@run_on_executor
	@emit_runtime_metrics( "start_php73_codebuild" )
	def start_php73_codebuild( self, credentials, libraries_object ):
		return TaskSpawner._start_php73_codebuild(
			self.aws_client_factory,
			credentials,
			libraries_object
		)

	@staticmethod
	def _start_php73_codebuild( aws_client_factory, credentials, libraries_object ):
		"""
		Returns a build ID to be polled at a later time
		"""
		codebuild_client = aws_client_factory.get_aws_client(
			"codebuild",
			credentials
		)

		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		commands = []

		for key, value in libraries_object.iteritems():
			commands.append(
				"composer require " + key
			)

		# Create empty zip file
		codebuild_zip = io.BytesIO( EMPTY_ZIP_DATA )

		buildspec_template = {
			"artifacts": {
				"files": [
					"**/*"
				]
			},
			"phases": {
				"build": {
					"commands": commands
				},
				"install": {
					"runtime-versions": {
						"php": 7.3
					}
				}
			},
			"version": 0.2
		}

		with zipfile.ZipFile( codebuild_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			# Write buildspec.yml defining the build process
			buildspec = zipfile.ZipInfo(
				"buildspec.yml"
			)
			buildspec.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				buildspec,
				yaml.dump(
					buildspec_template
				)
			)

		codebuild_zip_data = codebuild_zip.getvalue()
		codebuild_zip.close()

		# S3 object key of the build package, randomly generated.
		s3_key = "buildspecs/" + str( uuid.uuid4() ) + ".zip"

		# Write the CodeBuild build package to S3
		s3_response = s3_client.put_object(
			Bucket=credentials[ "lambda_packages_bucket" ],
			Body=codebuild_zip_data,
			Key=s3_key,
			ACL="public-read", # THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
		)

		# Fire-off the build
		codebuild_response = codebuild_client.start_build(
			projectName="refinery-builds",
			sourceTypeOverride="S3",
			sourceLocationOverride=credentials[ "lambda_packages_bucket" ] + "/" + s3_key,
		)

		build_id = codebuild_response[ "build" ][ "id" ]

		return build_id

	@staticmethod
	def _get_php_73_base_code( app_config, code ):
		code = re.sub(
			r"function main\([^\)]+\)[^{]\{",
			"function main( $block_input ) {global $backpack;",
			code
		)

		code = code.replace(
			"require __DIR__",
			"require $_ENV[\"LAMBDA_TASK_ROOT\"]"
		)

		code = code + "\n\n" + app_config.get( "LAMDBA_BASE_CODES" )[ "php7.3" ]
		return code

	@staticmethod
	def _build_php_73_lambda( app_config, aws_client_factory, credentials, code, libraries ):
		code = TaskSpawner._get_php_73_base_code(
			app_config,
			code
		)

		# Use CodeBuilder to get a base zip of the libraries
		base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
		if len( libraries ) > 0:
			base_zip_data = TaskSpawner._get_php73_lambda_base_zip(
				aws_client_factory,
				credentials,
				libraries
			)

		# Create a virtual file handler for the Lambda zip package
		lambda_package_zip = io.BytesIO( base_zip_data )

		with zipfile.ZipFile( lambda_package_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			info = zipfile.ZipInfo(
				"lambda"
			)
			info.external_attr = 0777 << 16L

			# Write lambda.php into new .zip
			zip_file_handler.writestr(
				info,
				str( code )
			)

		lambda_package_zip_data = lambda_package_zip.getvalue()
		lambda_package_zip.close()

		return lambda_package_zip_data

	@staticmethod
	def _get_go_112_base_code( app_config, code ):
		code = code + "\n\n" + app_config.get( "LAMDBA_BASE_CODES" )[ "go1.12" ]
		return code

	@staticmethod
	def _get_ruby_264_base_code( app_config, code ):
		code = code + "\n\n" + app_config.get( "LAMDBA_BASE_CODES" )[ "ruby2.6.4" ]
		return code

	@staticmethod
	def _build_ruby_264_lambda( app_config, aws_client_factory, credentials, code, libraries ):
		code = TaskSpawner._get_ruby_264_base_code(
			app_config,
			code
		)

		# Use CodeBuilder to get a base zip of the libraries
		base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )

		if len( libraries ) > 0:
			base_zip_data = TaskSpawner._get_ruby_264_lambda_base_zip(
				aws_client_factory,
				credentials,
				libraries
			)

		# Create a virtual file handler for the Lambda zip package
		lambda_package_zip = io.BytesIO( base_zip_data )

		with zipfile.ZipFile( lambda_package_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			info = zipfile.ZipInfo(
				"lambda"
			)
			info.external_attr = 0777 << 16L

			# Write lambda.py into new .zip
			zip_file_handler.writestr(
				info,
				str( code )
			)

		lambda_package_zip_data = lambda_package_zip.getvalue()
		lambda_package_zip.close()

		return lambda_package_zip_data

	@staticmethod
	def _get_nodejs_10163_base_code( app_config, code ):
		code = re.sub(
			r"function main\([^\)]+\)[^{]\{",
			"function main( blockInput ) {",
			code
		)

		code = re.sub(
			r"function mainCallback\([^\)]+\)[^{]\{",
			"function mainCallback( blockInput, callback ) {",
			code
		)

		code = code + "\n\n" + app_config.get( "LAMDBA_BASE_CODES" )[ "nodejs10.16.3" ]
		return code

	@staticmethod
	def _build_nodejs_10163_lambda( app_config, aws_client_factory, credentials, code, libraries ):
		code = TaskSpawner._get_nodejs_10163_base_code(
			app_config,
			code
		)

		# Use CodeBuilder to get a base zip of the libraries
		base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
		if len( libraries ) > 0:
			base_zip_data = TaskSpawner._get_nodejs_10163_lambda_base_zip(
				aws_client_factory,
				credentials,
				libraries
			)

		# Create a virtual file handler for the Lambda zip package
		lambda_package_zip = io.BytesIO( base_zip_data )

		with zipfile.ZipFile( lambda_package_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			info = zipfile.ZipInfo(
				"lambda"
			)
			info.external_attr = 0777 << 16L

			# Write lambda.py into new .zip
			zip_file_handler.writestr(
				info,
				str( code )
			)

		lambda_package_zip_data = lambda_package_zip.getvalue()
		lambda_package_zip.close()

		return lambda_package_zip_data

	@staticmethod
	def _get_nodejs_10163_lambda_base_zip( aws_client_factory, credentials, libraries ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		libraries_object = {}
		for library in libraries:
			libraries_object[ str( library ) ] = "latest"

		final_s3_package_zip_path = TaskSpawner._get_final_zip_package_path(
			"nodejs10.16.3",
			libraries_object
		)

		if TaskSpawner._s3_object_exists( aws_client_factory, credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
			return TaskSpawner._read_from_s3(
				aws_client_factory,
				credentials,
				credentials[ "lambda_packages_bucket" ],
				final_s3_package_zip_path
			)

		# Kick off CodeBuild for the libraries to get a zip artifact of
		# all of the libraries.
		build_id = TaskSpawner._start_node10163_codebuild(
			aws_client_factory,
			credentials,
			libraries_object
		)

		# This continually polls for the CodeBuild build to finish
		# Once it does it returns the raw artifact zip data.
		return TaskSpawner._get_codebuild_artifact_zip_data(
			aws_client_factory,
			credentials,
			build_id,
			final_s3_package_zip_path
		)

	@run_on_executor
	@emit_runtime_metrics( "start_node10163_codebuild" )
	def start_node10163_codebuild( self, credentials, libraries_object ):
		return TaskSpawner._start_node810_codebuild(
			self.aws_client_factory,
			credentials,
			libraries_object
		)

	@staticmethod
	def _start_node10163_codebuild( aws_client_factory, credentials, libraries_object ):
		"""
		Returns a build ID to be polled at a later time
		"""
		codebuild_client = aws_client_factory.get_aws_client(
			"codebuild",
			credentials
		)

		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials
		)

		package_json_template = {
			"name": "refinery-lambda",
			"version": "1.0.0",
			"description": "Lambda created by Refinery",
			"main": "main.js",
			"dependencies": libraries_object,
			"devDependencies": {},
			"scripts": {}
		}

		# Create empty zip file
		codebuild_zip = io.BytesIO( EMPTY_ZIP_DATA )

		buildspec_template = {
			"artifacts": {
				"files": [
					"**/*"
				]
			},
			"phases": {
				"build": {
					"commands": [
						"npm install"
					]
				},
				"install": {
					"runtime-versions": {
						"nodejs": 10
					}
				}
			},
			"version": 0.2
		}

		with zipfile.ZipFile( codebuild_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			# Write buildspec.yml defining the build process
			buildspec = zipfile.ZipInfo(
				"buildspec.yml"
			)
			buildspec.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				buildspec,
				yaml.dump(
					buildspec_template
				)
			)

			# Write the package.json
			package_json = zipfile.ZipInfo(
				"package.json"
			)
			package_json.external_attr = 0777 << 16L
			zip_file_handler.writestr(
				package_json,
				json.dumps(
					package_json_template
				)
			)

		codebuild_zip_data = codebuild_zip.getvalue()
		codebuild_zip.close()

		# S3 object key of the build package, randomly generated.
		s3_key = "buildspecs/" + str( uuid.uuid4() ) + ".zip"

		# Write the CodeBuild build package to S3
		s3_response = s3_client.put_object(
			Bucket=credentials[ "lambda_packages_bucket" ],
			Body=codebuild_zip_data,
			Key=s3_key,
			ACL="public-read", # THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
		)

		# Fire-off the build
		codebuild_response = codebuild_client.start_build(
			projectName="refinery-builds",
			sourceTypeOverride="S3",
			sourceLocationOverride=credentials[ "lambda_packages_bucket" ] + "/" + s3_key,
		)

		build_id = codebuild_response[ "build" ][ "id" ]

		return build_id

	@staticmethod
	def _get_nodejs_810_base_code( app_config, code ):
		code = re.sub(
			r"function main\([^\)]+\)[^{]\{",
			"function main( blockInput ) {",
			code
		)

		code = re.sub(
			r"function mainCallback\([^\)]+\)[^{]\{",
			"function mainCallback( blockInput, callback ) {",
			code
		)

		code = code + "\n\n" + app_config.get( "LAMDBA_BASE_CODES" )[ "nodejs8.10" ]
		return code

	@staticmethod
	def _build_nodejs_810_lambda( app_config, aws_client_factory, credentials, code, libraries ):
		code = TaskSpawner._get_nodejs_810_base_code(
			app_config,
			code
		)

		# Use CodeBuilder to get a base zip of the libraries
		base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
		if len( libraries ) > 0:
			base_zip_data = TaskSpawner._get_nodejs_810_lambda_base_zip(
				aws_client_factory,
				credentials,
				libraries
			)

		# Create a virtual file handler for the Lambda zip package
		lambda_package_zip = io.BytesIO( base_zip_data )

		with zipfile.ZipFile( lambda_package_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			info = zipfile.ZipInfo(
				"lambda"
			)
			info.external_attr = 0777 << 16L

			# Write lambda.py into new .zip
			zip_file_handler.writestr(
				info,
				str( code )
			)

		lambda_package_zip_data = lambda_package_zip.getvalue()
		lambda_package_zip.close()

		return lambda_package_zip_data

	@staticmethod
	def _get_python36_base_code( app_config, code ):
		code = code + "\n\n" + app_config.get( "LAMDBA_BASE_CODES" )[ "python3.6" ]
		return code

	@staticmethod
	def _build_python36_lambda( app_config, aws_client_factory, credentials, code, libraries ):
		code = TaskSpawner._get_python36_base_code(
			app_config,
			code
		)

		base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
		if len( libraries ) > 0:
			base_zip_data = TaskSpawner._get_python36_lambda_base_zip(
				aws_client_factory,
				credentials,
				libraries
			)

		# Create a virtual file handler for the Lambda zip package
		lambda_package_zip = io.BytesIO( base_zip_data )

		with zipfile.ZipFile( lambda_package_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			info = zipfile.ZipInfo(
				"lambda"
			)
			info.external_attr = 0777 << 16L

			# Write lambda.py into new .zip
			zip_file_handler.writestr(
				info,
				str( code )
			)

		lambda_package_zip_data = lambda_package_zip.getvalue()
		lambda_package_zip.close()

		return lambda_package_zip_data

	@staticmethod
	def _get_python27_base_code( app_config, code ):
		code = code + "\n\n" + app_config.get( "LAMDBA_BASE_CODES" )[ "python2.7" ]
		return code

	@staticmethod
	def _build_python27_lambda( app_config, aws_client_factory, credentials, code, libraries ):
		"""
		Build Lambda package zip and return zip data
		"""

		"""
		Inject base libraries (e.g. redis) into lambda
		and the init code.
		"""

		# Get customized base code
		code = TaskSpawner._get_python27_base_code(
			app_config,
			code
		)

		base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
		if len( libraries ) > 0:
			base_zip_data = TaskSpawner._get_python27_lambda_base_zip(
				aws_client_factory,
				credentials,
				libraries
			)

		# Create a virtual file handler for the Lambda zip package
		lambda_package_zip = io.BytesIO( base_zip_data )

		with zipfile.ZipFile( lambda_package_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			info = zipfile.ZipInfo(
				"lambda"
			)
			info.external_attr = 0777 << 16L

			# Write lambda.py into new .zip
			zip_file_handler.writestr(
				info,
				str( code )
			)

		lambda_package_zip_data = lambda_package_zip.getvalue()
		lambda_package_zip.close()

		return lambda_package_zip_data

	@staticmethod
	def _automatically_fix_schedule_expression( schedule_expression ):
		# Trim whitespace
		schedule_expression = schedule_expression.strip()

		# The known bad cases we want to auto-fix
		known_bad_cases = [
			"rate(1 minutes)",
			"rate(1 hours)",
			"rate(1 days)",
		]

		if schedule_expression in known_bad_cases:
			return re.sub(
				"s\)$",
				")",
				schedule_expression
			)

		# Check if they're doing the explicitly-correct non-plural case
		# If so we can just return it as-is
		for known_bad_case in known_bad_cases:
			if schedule_expression == known_bad_case.replace( "s)", ")" ):
				return schedule_expression

		# Outside of the above cases it should always be plural
		if not ( schedule_expression.endswith( "s)" ) ):
			return re.sub(
				"\)$",
				"s)",
				schedule_expression
			)

		return schedule_expression

	@run_on_executor
	@emit_runtime_metrics( "create_cloudwatch_group" )
	def create_cloudwatch_group( self, credentials, group_name, tags_dict, retention_days ):
		# Create S3 client
		cloudwatch_logs = self.aws_client_factory.get_aws_client(
			"logs",
			credentials
		)

		response = cloudwatch_logs.create_log_group(
			logGroupName=group_name,
			tags=tags_dict
		)

		retention_response = cloudwatch_logs.put_retention_policy(
			logGroupName=group_name,
			retentionInDays=retention_days
		)

		return {
			"group_name": group_name,
			"tags_dict": tags_dict
		}

	@run_on_executor
	@emit_runtime_metrics( "create_cloudwatch_rule" )
	def create_cloudwatch_rule( self, credentials, id, name, schedule_expression, description, input_string ):
		events_client = self.aws_client_factory.get_aws_client(
			"events",
			credentials,
		)

		schedule_expression = TaskSpawner._automatically_fix_schedule_expression( schedule_expression )

		# Events role ARN is able to be generated off of the account ID
		# The role name should be the same for all accounts.
		events_role_arn = "arn:aws:iam::" + str( credentials[ "account_id" ] ) + ":role/refinery_default_aws_cloudwatch_role"

		response = events_client.put_rule(
			Name=name,
			ScheduleExpression=schedule_expression, # cron(0 20 * * ? *) or rate(5 minutes)
			State="ENABLED",
			Description=description,
			RoleArn=events_role_arn
		)

		rule_arn = response[ "RuleArn" ]

		tag_add_response = events_client.tag_resource(
			ResourceARN=rule_arn,
			Tags=[
				{
					"Key": "RefineryResource",
					"Value": "true"
				},
			]
		)

		return {
			"id": id,
			"name": name,
			"arn": rule_arn,
			"input_string": input_string,
		}

	@run_on_executor
	@emit_runtime_metrics( "add_rule_target" )
	def add_rule_target( self, credentials, rule_name, target_id, target_arn, input_string ):
		# Automatically parse JSON
		try:
			input_string = json.loads(
				input_string
			)
		except:
			pass

		events_client = self.aws_client_factory.get_aws_client(
			"events",
			credentials,
		)

		lambda_client = self.aws_client_factory.get_aws_client(
			"lambda",
			credentials,
		)

		targets_data =	 {
			"Id": target_id,
			"Arn": target_arn,
			"Input": json.dumps(
				input_string
			)
		}

		rule_creation_response = events_client.put_targets(
			Rule=rule_name,
			Targets=[
				targets_data
			]
		)

		"""
		For AWS Lambda you need to add a permission to the Lambda function itself
		via the add_permission API call to allow invocation via the CloudWatch event.
		"""
		lambda_permission_add_response = lambda_client.add_permission(
			FunctionName=target_arn,
			StatementId=rule_name + "_statement",
			Action="lambda:*",
			Principal="events.amazonaws.com",
			SourceArn="arn:aws:events:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":rule/" + rule_name,
			#SourceAccount=self.app_config.get( "aws_account_id" ) # THIS IS A BUG IN AWS NEVER PASS THIS
		)

		return rule_creation_response

	@run_on_executor
	@emit_runtime_metrics( "create_sns_topic" )
	def create_sns_topic( self, credentials, id, topic_name ):
		sns_client = self.aws_client_factory.get_aws_client(
			"sns",
			credentials
		)

		topic_name = get_lambda_safe_name( topic_name )
		response = sns_client.create_topic(
			Name=topic_name,
			Tags=[
				{
					"Key": "RefineryResource",
					"Value": "true"
				},
			]
		)

		return {
			"id": id,
			"name": topic_name,
			"arn": response[ "TopicArn" ]
		}

	@run_on_executor
	@emit_runtime_metrics( "subscribe_lambda_to_sns_topic" )
	def subscribe_lambda_to_sns_topic( self, credentials, topic_arn, lambda_arn ):
		"""
		For AWS Lambda you need to add a permission to the Lambda function itself
		via the add_permission API call to allow invocation via the SNS event.
		"""
		lambda_client = self.aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)

		sns_client = self.aws_client_factory.get_aws_client(
			"sns",
			credentials,
		)

		lambda_permission_add_response = lambda_client.add_permission(
			FunctionName=lambda_arn,
			StatementId=str( uuid.uuid4() ),
			Action="lambda:*",
			Principal="sns.amazonaws.com",
			SourceArn=topic_arn,
			#SourceAccount=self.app_config.get( "aws_account_id" ) # THIS IS A BUG IN AWS NEVER PASS THIS
		)

		sns_topic_response = sns_client.subscribe(
			TopicArn=topic_arn,
			Protocol="lambda",
			Endpoint=lambda_arn,
			Attributes={},
			ReturnSubscriptionArn=True
		)

		return {
			"statement": lambda_permission_add_response[ "Statement" ],
			"arn": sns_topic_response[ "SubscriptionArn" ]
		}

	@run_on_executor
	@emit_runtime_metrics( "create_sqs_queue" )
	def create_sqs_queue( self, credentials, id, queue_name, batch_size, visibility_timeout ):
		sqs_client = self.aws_client_factory.get_aws_client(
			"sqs",
			credentials
		)

		sqs_queue_name = get_lambda_safe_name( queue_name )

		queue_deleted = False

		while queue_deleted == False:
			try:
				sqs_response = sqs_client.create_queue(
					QueueName=sqs_queue_name,
					Attributes={
						"DelaySeconds": str( 0 ),
						"MaximumMessageSize": "262144",
						"VisibilityTimeout": str( visibility_timeout ), # Lambda max time plus ten seconds
					}
				)

				queue_deleted = True
			except sqs_client.exceptions.QueueDeletedRecently:
				logit( "SQS queue was deleted too recently, trying again in ten seconds..." )

				time.sleep( 10 )

		sqs_arn = "arn:aws:sqs:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + queue_name
		sqs_url = "https://sqs." + credentials[ "region" ] + ".amazonaws.com/" + str( credentials[ "account_id" ] ) + "/" + queue_name

		sqs_tag_queue_response = sqs_client.tag_queue(
			QueueUrl=sqs_url,
			Tags={
				"RefineryResource": "true"
			}
		)

		return {
			"id": id,
			"name": queue_name,
			"arn": sqs_arn,
			"batch_size": batch_size
		}

	@run_on_executor
	@emit_runtime_metrics( "map_sqs_to_lambda" )
	def map_sqs_to_lambda( self, credentials, sqs_arn, lambda_arn, batch_size ):
		lambda_client = self.aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)

		response = lambda_client.create_event_source_mapping(
			EventSourceArn=sqs_arn,
			FunctionName=lambda_arn,
			Enabled=True,
			BatchSize=batch_size,
		)

		return response

	@run_on_executor
	@emit_runtime_metrics( "read_from_s3_and_return_input" )
	def read_from_s3_and_return_input( self, credentials, s3_bucket, path ):
		return_data = TaskSpawner._read_from_s3(
			self.aws_client_factory,
			credentials,
			s3_bucket,
			path
		)

		return {
			"s3_bucket": s3_bucket,
			"path": path,
			"body": return_data
		}

	@run_on_executor
	@emit_runtime_metrics( "read_from_s3" )
	def read_from_s3( self, credentials, s3_bucket, path ):
		return TaskSpawner._read_from_s3(
			self.aws_client_factory,
			credentials,
			s3_bucket,
			path
		)

	@staticmethod
	def _read_from_s3( aws_client_factory, credentials, s3_bucket, path ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials,
		)

		# Remove leading / because they are almost always not intended
		if path.startswith( "/" ):
			path = path[1:]

		try:
			s3_object = s3_client.get_object(
				Bucket=s3_bucket,
				Key=path
			)
		except:
			return "{}"

		return s3_object[ "Body" ].read()

	@run_on_executor
	@emit_runtime_metrics( "bulk_s3_delete" )
	def bulk_s3_delete( self, credentials, s3_bucket, s3_path_list ):
		s3_client = self.aws_client_factory.get_aws_client(
			"s3",
			credentials,
		)

		delete_data = []

		for s3_path in s3_path_list:
			delete_data.append({
				"Key": s3_path,
			})

		response = s3_client.delete_objects(
			Bucket=s3_bucket,
			Delete={
				"Objects": delete_data
			},
		)

		return response

	@run_on_executor
	@emit_runtime_metrics( "get_s3_pipeline_execution_logs" )
	def get_s3_pipeline_execution_logs( self, credentials, s3_prefix, max_results ):
		return TaskSpawner._get_all_s3_paths(
			self.aws_client_factory,
			credentials,
			credentials[ "logs_bucket" ],
			s3_prefix,
			max_results
		)

	@run_on_executor
	@emit_runtime_metrics( "get_build_packages" )
	def get_build_packages( self, credentials, s3_prefix, max_results ):
		return TaskSpawner._get_all_s3_paths(
			self.aws_client_factory,
			credentials,
			credentials[ "lambda_packages_bucket" ],
			s3_prefix,
			max_results
		)

	@run_on_executor
	@emit_runtime_metrics( "get_s3_list_from_prefix" )
	def get_s3_list_from_prefix( self, credentials, s3_bucket, s3_prefix, continuation_token, start_after ):
		s3_client = self.aws_client_factory.get_aws_client(
			"s3",
			credentials,
		)

		s3_options = {
			"Bucket": s3_bucket,
			"Prefix": s3_prefix,
			"Delimiter": "/",
			"MaxKeys": 1000,
		}

		if continuation_token:
			s3_options[ "ContinuationToken" ] = continuation_token

		if start_after:
			s3_options[ "StartAfter" ] = start_after

		object_list_response = s3_client.list_objects_v2(
			**s3_options
		)

		common_prefixes = []

		# Handle the case of no prefixs (no logs written yet)
		if not ( "CommonPrefixes" in object_list_response ):
			return {
				"common_prefixes": [],
				"continuation_token": False
			}

		for result in object_list_response[ "CommonPrefixes" ]:
			common_prefixes.append(
				result[ "Prefix" ]
			)

		if "NextContinuationToken" in object_list_response:
			continuation_token = object_list_response[ "NextContinuationToken" ]

		# Sort list of prefixs to keep then canonicalized
		# for the hash key used to determine if we need to
		# re-partition the Athena table.
		common_prefixes.sort()

		return {
			"common_prefixes": common_prefixes,
			"continuation_token": continuation_token
		}

	@staticmethod
	def _get_all_s3_paths( aws_client_factory, credentials, s3_bucket, prefix, max_results, **kwargs ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials,
		)

		return_array = []
		continuation_token = False
		if max_results == -1:  # max_results -1 means get all results
			max_keys = 1000
		elif max_results <= 1000:
			max_keys = max_results
		else:
			max_keys = 1000

		# First check to prime it
		response = s3_client.list_objects_v2(
			Bucket=s3_bucket,
			Prefix=prefix,
			MaxKeys=max_keys,  # Max keys you can request at once
			**kwargs
		)

		# Only list up to 10k pages (I hope this never happens!)
		for _ in xrange(10000):
			if continuation_token:
				# Grab another page of results
				response = s3_client.list_objects_v2(
					Bucket=s3_bucket,
					Prefix=prefix,
					MaxKeys=max_keys,  # Max keys you can request at once
					ContinuationToken=continuation_token,
					**kwargs
				)

			if not ( "Contents" in response ):
				break

			for s3_object in response[ "Contents" ]:
				return_array.append(
					s3_object[ "Key" ]
				)

			# If the length is longer than the max results amount
			# then just return the data.
			if ( max_results != -1 ) and max_results <= len( return_array ):
				break

			if not response[ "IsTruncated" ]:
				break

			continuation_token = response[ "NextContinuationToken" ]

		return return_array

	@run_on_executor
	@emit_runtime_metrics( "get_s3_pipeline_execution_ids" )
	def get_s3_pipeline_execution_ids( self, credentials, timestamp_prefix, max_results, continuation_token ):
		return TaskSpawner._get_all_s3_prefixes(
			self.aws_client_factory,
			credentials,
			credentials[ "logs_bucket" ],
			timestamp_prefix,
			max_results,
			continuation_token
		)

	@run_on_executor
	@emit_runtime_metrics( "get_s3_pipeline_timestamp_prefixes" )
	def get_s3_pipeline_timestamp_prefixes( self, credentials, project_id, max_results, continuation_token ):
		return TaskSpawner._get_all_s3_prefixes(
			self.aws_client_factory,
			credentials,
			credentials[ "logs_bucket" ],
			project_id + "/",
			max_results,
			continuation_token
		)

	@staticmethod
	def _get_all_s3_prefixes( aws_client_factory, credentials, s3_bucket, prefix, max_results, continuation_token ):
		s3_client = aws_client_factory.get_aws_client(
			"s3",
			credentials,
		)

		return_array = []
		if max_results == -1: # max_results -1 means get all results
			max_keys = 1000
		elif max_results <= 1000:
			max_keys = max_results
		else:
			max_keys = 1000

		list_objects_params = {
			"Bucket": s3_bucket,
			"Prefix": prefix,
			"MaxKeys": max_keys, # Max keys you can request at once
			"Delimiter": "/"
		}

		if continuation_token:
			list_objects_params[ "ContinuationToken" ] = continuation_token

		# First check to prime it
		response = s3_client.list_objects_v2(
			**list_objects_params
		)

		# Bound this loop to only execute MAX_LOOP_ITERATION times since we
		# cannot guarantee that the condition `continuation_token == False`
		# will ever be true.
		for _ in xrange(1000):
			if continuation_token:
				list_objects_params[ "ContinuationToken" ] = continuation_token
				# Grab another page of results
				response = s3_client.list_objects_v2(
					**list_objects_params
				)

			if "NextContinuationToken" in response:
				continuation_token = response[ "NextContinuationToken" ]
			else:
				continuation_token = False

			# No results
			if not ( "CommonPrefixes" in response ):
				break

			for s3_prefix in response[ "CommonPrefixes" ]:
				return_array.append(
					s3_prefix[ "Prefix" ]
				)

			# If the length is longer than the max results amount
			# then just return the data.
			if ( max_results != -1 ) and max_results <= len( return_array ):
				break

			if not response[ "IsTruncated" ]:
				break

		return {
			"prefixes": return_array,
			"continuation_token": continuation_token
		}

	@run_on_executor
	@emit_runtime_metrics( "get_aws_lambda_existence_info" )
	def get_aws_lambda_existence_info( self, credentials, _id, _type, lambda_name ):
		return TaskSpawner._get_aws_lambda_existence_info( self.aws_client_factory, credentials, _id, _type, lambda_name )

	@staticmethod
	def _get_aws_lambda_existence_info( aws_client_factory, credentials, _id, _type, lambda_name ):
		lambda_client = aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)

		try:
			response = lambda_client.get_function(
				FunctionName=lambda_name
			)
		except lambda_client.exceptions.ResourceNotFoundException:
			return {
				"id": _id,
				"type": _type,
				"name": lambda_name,
				"exists": False
			}

		return {
			"id": _id,
			"type": _type,
			"name": lambda_name,
			"exists": True,
			"arn": response[ "Configuration" ][ "FunctionArn" ]
		}

	@run_on_executor
	@emit_runtime_metrics( "get_lambda_cloudwatch_logs" )
	def get_lambda_cloudwatch_logs( self, credentials, log_group_name, stream_id ):
		return TaskSpawner._get_lambda_cloudwatch_logs( self.aws_client_factory, credentials, log_group_name, stream_id )

	@staticmethod
	def _get_lambda_cloudwatch_logs( aws_client_factory, credentials, log_group_name, stream_id ):
		cloudwatch_logs_client = aws_client_factory.get_aws_client(
			"logs",
			credentials
		)

		if not stream_id:
			# Pull the last stream from CloudWatch
			# Streams take time to propagate so wait if needed
			streams_data = cloudwatch_logs_client.describe_log_streams(
				logGroupName=log_group_name,
				orderBy="LastEventTime",
				limit=50
			)

			stream_id = streams_data[ "logStreams" ][ 0 ][ "logStreamName" ]

		log_output = ""
		attempts_remaining = 4
		some_log_data_returned = False
		forward_token = False
		last_forward_token = False

		while attempts_remaining > 0:
			logit( "[ STATUS ] Grabbing log events from '" + log_group_name + "' at '" + stream_id + "'..." )
			get_log_events_params = {
				"logGroupName": log_group_name,
				"logStreamName": stream_id
			}

			if forward_token:
				get_log_events_params[ "nextToken" ] = forward_token

			log_data = cloudwatch_logs_client.get_log_events(
				**get_log_events_params
			)

			last_forward_token = forward_token
			forward_token = False
			forward_token = log_data[ "nextForwardToken" ]

			# If we got nothing in response we'll try again
			if len( log_data[ "events" ] ) == 0 and some_log_data_returned == False:
				attempts_remaining = attempts_remaining - 1
				time.sleep( 1 )
				continue

			# If that's the last of the log data, quit out
			if last_forward_token == forward_token:
				break

			# Indicate we've at least gotten some log data previously
			some_log_data_returned = True

			for event_data in log_data[ "events" ]:
				# Append log data
				log_output += event_data[ "message" ]

		return log_output

	@run_on_executor
	@emit_runtime_metrics( "get_cloudwatch_existence_info" )
	def get_cloudwatch_existence_info( self, credentials, _id, _type, name ):
		return TaskSpawner._get_cloudwatch_existence_info( self.aws_client_factory, credentials, _id, _type, name )

	@staticmethod
	def _get_cloudwatch_existence_info( aws_client_factory, credentials, _id, _type, name ):
		events_client = aws_client_factory.get_aws_client(
			"events",
			credentials
		)

		try:
			response = events_client.describe_rule(
				Name=name,
			)
		except events_client.exceptions.ResourceNotFoundException:
			return {
				"id": _id,
				"type": _type,
				"name": name,
				"exists": False
			}

		return {
			"id": _id,
			"type": _type,
			"name": name,
			"arn": response[ "Arn" ],
			"exists": True,
		}

	@run_on_executor
	@emit_runtime_metrics( "get_sqs_existence_info" )
	def get_sqs_existence_info( self, credentials, _id, _type, name ):
		return TaskSpawner._get_sqs_existence_info( self.aws_client_factory, credentials, _id, _type, name )

	@staticmethod
	def _get_sqs_existence_info( aws_client_factory, credentials, _id, _type, name ):
		sqs_client = aws_client_factory.get_aws_client(
			"sqs",
			credentials,
		)

		try:
			queue_url_response = sqs_client.get_queue_url(
				QueueName=name,
			)
		except sqs_client.exceptions.QueueDoesNotExist:
			return {
				"id": _id,
				"type": _type,
				"name": name,
				"exists": False
			}

		return {
			"id": _id,
			"type": _type,
			"name": name,
			"arn": "arn:aws:sqs:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + name,
			"exists": True,
		}

	@run_on_executor
	@emit_runtime_metrics( "get_sns_existence_info" )
	def get_sns_existence_info( self, credentials, _id, _type, name ):
		return TaskSpawner._get_sns_existence_info(
			self.aws_client_factory, credentials, _id, _type, name )

	@staticmethod
	def _get_sns_existence_info( aws_client_factory, credentials, _id, _type, name ):
		sns_client = aws_client_factory.get_aws_client(
			"sns",
			credentials
		)

		sns_topic_arn = "arn:aws:sns:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + name

		try:
			response = sns_client.get_topic_attributes(
				TopicArn=sns_topic_arn
			)
		except sns_client.exceptions.NotFoundException:
			return {
				"id": _id,
				"type": _type,
				"name": name,
				"exists": False
			}

		return {
			"id": _id,
			"type": _type,
			"name": name,
			"arn": sns_topic_arn,
			"exists": True,
		}

	@run_on_executor
	@emit_runtime_metrics( "create_rest_api" )
	def create_rest_api( self, credentials, name, description, version ):
		api_gateway_client = self.aws_client_factory.get_aws_client(
			"apigateway",
			credentials
		)

		response = api_gateway_client.create_rest_api(
			name=name,
			description=description,
			version=version,
			apiKeySource="HEADER",
			endpointConfiguration={
				"types": [
					"EDGE",
				]
			},
			binaryMediaTypes=[
				"*/*"
			],
			tags={
				"RefineryResource": "true"
			}
		)

		return {
			"id": response[ "id" ],
			"name": response[ "name" ],
			"description": response[ "description" ],
			"version": response[ "version" ]
		}

	@run_on_executor
	@emit_runtime_metrics( "deploy_api_gateway_to_stage" )
	def deploy_api_gateway_to_stage( self, credentials, rest_api_id, stage_name ):
		api_gateway_client = self.aws_client_factory.get_aws_client(
			"apigateway",
			credentials
		)

		deployment_response = api_gateway_client.create_deployment(
			restApiId=rest_api_id,
			stageName=stage_name,
			stageDescription="API Gateway deployment deployed via refinery",
			description="API Gateway deployment deployed via refinery"
		)

		deployment_id = deployment_response[ "id" ]

		return {
			"id": rest_api_id,
			"stage_name": stage_name,
			"deployment_id": deployment_id,
		}

	@run_on_executor
	@emit_runtime_metrics( "create_resource" )
	def create_resource( self, credentials, rest_api_id, parent_id, path_part ):
		api_gateway_client = self.aws_client_factory.get_aws_client(
			"apigateway",
			credentials
		)

		response = api_gateway_client.create_resource(
			restApiId=rest_api_id,
			parentId=parent_id,
			pathPart=path_part
		)

		return {
			"id": response[ "id" ],
			"api_gateway_id": rest_api_id,
			"parent_id": parent_id,
		}

	@run_on_executor
	@emit_runtime_metrics( "create_method" )
	def create_method( self, credentials, method_name, rest_api_id, resource_id, http_method, api_key_required ):
		api_gateway_client = self.aws_client_factory.get_aws_client(
			"apigateway",
			credentials
		)

		response = api_gateway_client.put_method(
			restApiId=rest_api_id,
			resourceId=resource_id,
			httpMethod=http_method,
			authorizationType="NONE",
			apiKeyRequired=api_key_required,
			operationName=method_name,
		)

		return {
			"method_name": method_name,
			"rest_api_id": rest_api_id,
			"resource_id": resource_id,
			"http_method": http_method,
			"api_key_required": api_key_required,
		}

	@run_on_executor
	@emit_runtime_metrics( "clean_lambda_iam_policies" )
	def clean_lambda_iam_policies( self, credentials, lambda_name ):
		lambda_client = self.aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)

		api_gateway_client = self.aws_client_factory.get_aws_client(
			"apigateway",
			credentials
		)

		logit( "Cleaning up IAM policies from no-longer-existing API Gateways attached to Lambda..." )
		try:
			response = lambda_client.get_policy(
				FunctionName=lambda_name,
			)
		except ClientError as e:
			if e.response[ "Error" ][ "Code" ] == "ResourceNotFoundException":
				return {}
			raise

		existing_lambda_statements = json.loads(
			response[ "Policy" ]
		)[ "Statement" ]

		for statement in existing_lambda_statements:
			# Try to extract API gateway
			try:
				source_arn = statement[ "Condition" ][ "ArnLike" ][ "AWS:SourceArn" ]
				arn_parts = source_arn.split( ":" )
			except:
				continue

			# Make sure it's an API Gateway policy
			if not source_arn.startswith( "arn:aws:execute-api:" ):
				continue

			try:
				api_gateway_id = arn_parts[ 5 ]
				api_gateway_data = api_gateway_client.get_rest_api(
					restApiId=api_gateway_id,
				)
			except:
				logit( "API Gateway does not exist, deleting IAM policy..." )

				delete_permission_response = lambda_client.remove_permission(
					FunctionName=lambda_name,
					StatementId=statement[ "Sid" ]
				)

		return {}

	@run_on_executor
	@emit_runtime_metrics( "add_integration_response" )
	def add_integration_response( self, credentials, rest_api_id, resource_id, http_method, lambda_name ):
		api_gateway_client = self.aws_client_factory.get_aws_client(
			"apigateway",
			credentials
		)
		response = api_gateway_client.put_integration_response(
			restApiId=rest_api_id,
			resourceId=resource_id,
			httpMethod=http_method,
			statusCode="200",
			contentHandling="CONVERT_TO_TEXT"
		)

	@run_on_executor
	@emit_runtime_metrics( "link_api_method_to_lambda" )
	def link_api_method_to_lambda( self, credentials, rest_api_id, resource_id, http_method, api_path, lambda_name ):
		api_gateway_client = self.aws_client_factory.get_aws_client(
			"apigateway",
			credentials
		)

		lambda_client = self.aws_client_factory.get_aws_client(
			"lambda",
			credentials
		)

		lambda_uri = "arn:aws:apigateway:" + credentials[ "region" ] + ":lambda:path/" + lambda_client.meta.service_model.api_version + "/functions/arn:aws:lambda:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":function:" + lambda_name + "/invocations"

		integration_response = api_gateway_client.put_integration(
			restApiId=rest_api_id,
			resourceId=resource_id,
			httpMethod=http_method,
			type="AWS_PROXY",
			integrationHttpMethod="POST", # MUST be POST: https://github.com/boto/boto3/issues/572#issuecomment-239294381
			uri=lambda_uri,
			connectionType="INTERNET",
			timeoutInMillis=29000 # 29 seconds
		)

		"""
		For AWS Lambda you need to add a permission to the Lambda function itself
		via the add_permission API call to allow invocation via the CloudWatch event.
		"""
		source_arn = "arn:aws:execute-api:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + rest_api_id + "/*/" + http_method + api_path

		# We have to clean previous policies we added from this Lambda
		# Scan over all policies and delete any which aren't associated with
		# API Gateways that actually exist!

		lambda_permission_add_response = lambda_client.add_permission(
			FunctionName=lambda_name,
			StatementId=str( uuid.uuid4() ).replace( "_", "" ) + "_statement",
			Action="lambda:*",
			Principal="apigateway.amazonaws.com",
			SourceArn=source_arn
		)

		return {
			"api_gateway_id": rest_api_id,
			"resource_id": resource_id,
			"http_method": http_method,
			"lambda_name": lambda_name,
			"type": integration_response[ "type" ],
			"arn": integration_response[ "uri" ],
			"statement": lambda_permission_add_response[ "Statement" ]
		}
