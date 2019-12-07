#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
import tornado.escape
import tornado.ioloop
import tornado.web
import subprocess
import sqlalchemy
import traceback
import functools
import botocore
import datetime
import requests
import pystache
import binascii
import hashlib
import ctypes
import shutil
import stripe
import base64
import string
import boto3
import numpy
import codecs
import struct
import uuid
import hmac
import json
import yaml
import copy
import math
import time
import jwt
import sys
import re
import os
import io

from tornado import gen
import unicodecsv as csv
from datetime import timedelta
from tornado.web import asynchronous
from ansi2html import Ansi2HTMLConverter
from botocore.exceptions import ClientError
from jsonschema import validate as validate_schema
from tornado.concurrent import run_on_executor, futures
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from email_validator import validate_email, EmailNotValidError

from utils.general import attempt_json_decode, logit, split_list_into_chunks, get_random_node_id, get_urand_password, get_random_id, get_random_deploy_id
from utils.ngrok import set_up_ngrok_websocket_tunnel
from utils.ip_lookup import get_external_ipv4_address
from utils.deployments.shared_files import add_shared_files_to_zip, get_shared_files_for_lambda
from utils.aws_client import get_aws_client, STS_CLIENT
from utils.deployments.teardown import teardown_infrastructure
from utils.deployments.awslambda import lambda_manager
from utils.deployments.api_gateway import api_gateway_manager, strip_api_gateway
from utils.deployments.shared_files import add_shared_files_to_zip, get_shared_files_for_lambda, add_shared_files_symlink_to_zip

from services.websocket_router import WebSocketRouter, run_scheduled_heartbeat

from controller.base import BaseHandler
from controller.executions_controller import ExecutionsControllerServer
from controller.lambda_connect_back import LambdaConnectBackServer
from controller.dangling_resources import CleanupDanglingResources
from controller.clear_invoice_drafts import ClearStripeInvoiceDrafts

from data_types.aws_resources.alambda import Lambda

from models.initiate_database import *
from models.saved_block import SavedBlock
from models.saved_block_version import SavedBlockVersion
from models.project_versions import ProjectVersion
from models.projects import Project
from models.organizations import Organization
from models.users import User
from models.email_auth_tokens import EmailAuthToken
from models.aws_accounts import AWSAccount
from models.deployments import Deployment
from models.project_config import ProjectConfig
from models.cached_billing_collections import CachedBillingCollection
from models.cached_billing_items import CachedBillingItem
from models.terraform_state_versions import TerraformStateVersion
from models.state_logs import StateLog
from models.cached_execution_logs_shard import CachedExecutionLogsShard
from models.project_short_links import ProjectShortLink
from models.inline_execution_lambdas import InlineExecutionLambda

from botocore.client import Config

try:
	# for Python 2.x
	from StringIO import StringIO
except ImportError:
	# for Python 3.x
	from io import StringIO

import zipfile

reload( sys )
sys.setdefaultencoding( "utf8" )

EMPTY_ZIP_DATA = bytearray( "PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" )

# Initialize Stripe
stripe.api_key = os.environ.get( "stripe_api_key" )

# Increase CSV field size to be the max
csv.field_size_limit( sys.maxsize )

# The WebSocket callback endpoint to use when live streaming the output
# of Lambdas via WebSockets.
LAMBDA_CALLBACK_ENDPOINT = False
			
def on_start():
	global LAMDBA_BASE_CODES, LAMBDA_BASE_LIBRARIES, LAMBDA_SUPPORTED_LANGUAGES, CUSTOM_RUNTIME_CODE, CUSTOM_RUNTIME_LANGUAGES, EMAIL_TEMPLATES, CUSTOMER_IAM_POLICY, DEFAULT_PROJECT_ARRAY, DEFAULT_PROJECT_CONFIG, NOT_SUPPORTED_INLINE_EXECUTION_LANGUAGES
	
	# Not-support inline execution languages (defaults to slower method)
	NOT_SUPPORTED_INLINE_EXECUTION_LANGUAGES = [
		"go1.12"
	]
	
	DEFAULT_PROJECT_CONFIG = {
		"version": "1.0.0",
		"environment_variables": {},
		"api_gateway": {
			"gateway_id": False,
		},
		"logging": {
			"level": "LOG_ALL",
		}
	}
	
	# Email templates
	email_templates_folder = "./email_templates/"
	EMAIL_TEMPLATES = {}
	for filename in os.listdir( email_templates_folder ):
		template_name = filename.split( "." )[0]
		with open( email_templates_folder + filename, "r" ) as file_handler:
			EMAIL_TEMPLATES[ template_name ] = file_handler.read()
	
	LAMDBA_BASE_CODES = {}
	
	# These languages are all custom
	CUSTOM_RUNTIME_LANGUAGES = [
		"nodejs8.10",
		"nodejs10.16.3",
		"php7.3",
		"go1.12",
		"python2.7",
		"python3.6",
		"ruby2.6.4"
	]
	
	LAMBDA_BASE_LIBRARIES = {
		"python3.6": [],
		"python2.7": [],
		"nodejs8.10": [],
		"nodejs10.16.3": [],
		"php7.3": [],
		"go1.12": [],
		"ruby2.6.4": []
	}
	
	LAMBDA_SUPPORTED_LANGUAGES = [
		"python3.6",
		"python2.7",
		"nodejs8.10",
		"nodejs10.16.3",
		"php7.3",
		"go1.12",
		"ruby2.6.4"
	]
	
	CUSTOM_RUNTIME_CODE = ""
	
	CUSTOMER_IAM_POLICY = ""
	
	# Load the default customer IAM policy
	with open( "./install/refinery-customer-iam-policy.json", "r" ) as file_handler:
		CUSTOMER_IAM_POLICY = json.loads(
			file_handler.read()
		)
	
	# Load the default bootstrap code
	with open( "./custom-runtime/base-src/bootstrap", "r" ) as file_handler:
		CUSTOM_RUNTIME_CODE = file_handler.read()

	for language_name, libraries in LAMBDA_BASE_LIBRARIES.iteritems():
		# Load Lambda base templates
		with open( "./lambda_bases/" + language_name, "r" ) as file_handler:
			LAMDBA_BASE_CODES[ language_name ] = file_handler.read()
			
	DEFAULT_PROJECT_ARRAY = []
	
	default_project_directory = "./default_projects/"
	
	for filename in os.listdir( default_project_directory ):
		with open( default_project_directory + filename, "r" ) as file_handler:
			DEFAULT_PROJECT_ARRAY.append(
				json.loads(
					file_handler.read()
				)
			)

mailgun_api_key = os.environ.get( "mailgun_api_key" )

if mailgun_api_key is None:
	print( "Please configure a Mailgun API key, this is needed for authentication and regular operations." )
	exit()

# This is purely for sending emails as part of Refinery's
# regular operations (e.g. authentication via email code, etc).
# This is Mailgun because SES is a huge PITA and is dragging their
# feet on verifying.

# This is another global Boto3 client because we need root access
# to pull the billing for all of our sub-accounts
COST_EXPLORER = boto3.client(
	"ce",
	aws_access_key_id=os.environ.get( "aws_access_key" ),
	aws_secret_access_key=os.environ.get( "aws_secret_key" ),
	region_name=os.environ.get( "region_name" ),
	config=Config(
		max_pool_connections=( 1000 * 2 )
	)
)

# The AWS organization API for provisioning new AWS sub-accounts
# for customers to use.
ORGANIZATION_CLIENT = boto3.client(
	"organizations",
	aws_access_key_id=os.environ.get( "aws_access_key" ),
	aws_secret_access_key=os.environ.get( "aws_secret_key" ),
	region_name=os.environ.get( "region_name" ),
	config=Config(
		max_pool_connections=( 1000 * 2 )
	)
)
		
"""
Decorators
"""
def authenticated( func ):
	"""
	Decorator to ensure the user is currently authenticated.
	
	If the user is not, the response will be:
	{
		"success": false,
		"code": "AUTH_REQUIRED",
		"msg": "...",
	}
	"""
	def wrapper( *args, **kwargs ):
		self_reference = args[0]
		
		authenticated_user = self_reference.get_authenticated_user()
		
		if authenticated_user == None:
			self_reference.write({
				"success": False,
				"code": "AUTH_REQUIRED",
				"msg": "You must be authenticated to do this!",
			})
			return
		
		return func( *args, **kwargs )
	return wrapper

def disable_on_overdue_payment( func ):
	"""
	Decorator to disable specific endpoints if the user
	is in collections and needs to settle up their bill.
	
	If the user is not, the response will be:
	{
		"success": false,
		"code": "ORGANIZATION_UNSETTLED_BILLS",
		"msg": "...",
	}
	"""
	def wrapper( *args, **kwargs ):
		self_reference = args[0]
		
		# Pull the authenticated user
		authenticated_user = self_reference.get_authenticated_user()
		
		# Pull the user's org to see if any payments are overdue
		authenticated_user_org = authenticated_user.organization
		
		if authenticated_user_org.payments_overdue == True:
			self_reference.write({
				"success": False,
				"code": "ORGANIZATION_UNSETTLED_BILLS",
				"msg": "This organization has an unsettled bill which is overdue for payment. This action can not be performed until the outstanding bills have been paid.",
			})
			return
		
		# Check if the user is on a free trial and if the free trial is over
		trial_info = get_user_free_trial_information( authenticated_user )
		
		if trial_info[ "is_using_trial" ] and trial_info[ "trial_over" ]:
			self_reference.write({
				"success": False,
				"code": "USER_FREE_TRIAL_ENDED",
				"msg": "Your free trial has ended, you must supply a payment method in order to perform this action.",
			})
			return
		
		return func( *args, **kwargs )
	return wrapper
	
def get_billing_rounded_float( input_price_float ):
	"""
	This is used because Stripe only allows you to charge line
	items in cents. Meaning that some rounding will occur on the
	final line items on the bill. AWS returns us lengthy-floats which
	means that the conversion will have to be done in both the invoice
	billing and the bill calculation endpoints the same way. We also have
	to do this in a safe round up way that won't accidentally under-bill
	our customers.
	
	This endpoint basically converts the AWS float into cents, rounds it,
	and then converts it back to a float rounded appropriately to two digits
	and returns the float again. All billing code should use this to ensure
	consistency in what the user sees from a billing point of view.
	"""
	# Special case is when the input float is 0
	if input_price_float == 0:
		return float( 0.00 )

	# Round float UP TO second digit
	# Meaning 10.015 becomes 10.02
	# and 10.012 becomes 10.02
	rounded_up_float = (
		math.ceil(
			input_price_float * 100
		) / 100
	)
	
	return rounded_up_float
	
# Custom exceptions
class CardIsPrimaryException(Exception):
    pass
    
class BuildException(Exception):
    def __init__( self, input_dict ):
    	self.msg = input_dict[ "msg" ]
    	self.build_output = input_dict[ "build_output" ]

# Regex for character whitelists for different fields
REGEX_WHITELISTS = {
	"arn": r"[^a-zA-Z0-9\:\_\-]+",
	"execution_pipeline_id": r"[^a-zA-Z0-9\-]+",
	"project_id": r"[^a-zA-Z0-9\-]+",
}

THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME = "RefinerySelfHostedLambdaRole"

class TaskSpawner(object):
		def __init__(self, loop=None):
			self.executor = futures.ThreadPoolExecutor( 60 )
			self.loop = loop or tornado.ioloop.IOLoop.current()
		
		@run_on_executor
		def create_third_party_aws_lambda_execute_role( self, credentials ):
			# Create IAM client
			iam_client = get_aws_client(
				"iam",
				credentials
			)
			
			assume_role_policy_doc = """{
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
}"""
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
		def get_json_from_s3( self, credentials, s3_bucket, s3_path ):
			# Create S3 client
			s3_client = get_aws_client(
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
		def write_json_to_s3( self, credentials, s3_bucket, s3_path, input_data ):
			# Create S3 client
			s3_client = get_aws_client(
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
		def get_block_executions( self, credentials, project_id, execution_pipeline_id, arn, oldest_timestamp ):
			return TaskSpawner._get_block_executions(
				credentials,
				project_id,
				execution_pipeline_id,
				arn,
				oldest_timestamp
			)

		@staticmethod
		def _get_block_executions( credentials, project_id, execution_pipeline_id, arn, oldest_timestamp ):
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

		@run_on_executor
		def get_project_execution_logs( self, credentials, project_id, oldest_timestamp ):
			return TaskSpawner._get_project_execution_logs(
				credentials,
				project_id,
				oldest_timestamp
			)

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

		@staticmethod
		def _get_project_execution_logs( credentials, project_id, oldest_timestamp ):
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
				credentials,
				query,
				True
			)

			# Convert the Athena query results into an execution pipeline ID with the
			# results sorted into a dictionary with the key beign the execution pipeline ID
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
		def create_project_id_log_table( self, credentials, project_id ):
			return TaskSpawner._create_project_id_log_table(
				credentials,
				project_id
			)

		@staticmethod
		def _create_project_id_log_table( credentials, project_id ):
			project_id = re.sub( REGEX_WHITELISTS[ "project_id" ], "", project_id )
			table_name = "PRJ_" + project_id.replace( "-", "_" )

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
			  'serialization.format' = '1'
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
				credentials,
				query,
				False
			)
			
		@run_on_executor
		def perform_athena_query( self, credentials, query, return_results ):
			return TaskSpawner._perform_athena_query(
				credentials,
				query,
				return_results
			)

		@staticmethod
		def _perform_athena_query( credentials, query, return_results ):
			athena_client = get_aws_client(
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
			while True:
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
			if return_results == False:
				return s3_object_location

			# Get S3 bucket and path from the s3 location string
			# s3://refinery-lambda-logging-uoits4nibdlslbq97qhfyb6ngkvzyewf/athena/
			s3_path = s3_object_location.replace(
				"s3://refinery-lambda-logging-" + credentials[ "s3_bucket_suffix" ],
				""
			)

			return TaskSpawner._get_athena_results_from_s3(
				credentials,
				"refinery-lambda-logging-" + credentials[ "s3_bucket_suffix" ],
				s3_path
			)

		@run_on_executor
		def get_athena_results_from_s3( self, credentials, s3_bucket, s3_path ):
			return TaskSpawner._get_athena_results_from_s3(
				credentials,
				s3_bucket,
				s3_path
			)

		@staticmethod
		def _get_athena_results_from_s3( credentials, s3_bucket, s3_path ):
			csv_data = TaskSpawner._read_from_s3(
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
		def _create_aws_org_sub_account( refinery_aws_account_id, email ):
			account_name = "Refinery Customer Account " + refinery_aws_account_id
			
			response = ORGANIZATION_CLIENT.create_account(
				Email=email,
				RoleName=os.environ.get( "customer_aws_admin_assume_role" ),
				AccountName=account_name,
				IamUserAccessToBilling="DENY"
			)
			account_status_data = response[ "CreateAccountStatus" ]
			create_account_id = account_status_data[ "Id" ]
			
			# Loop while the account is being created
			while True:
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
				response = ORGANIZATION_CLIENT.describe_create_account_status(
					CreateAccountRequestId=create_account_id
				)
				account_status_data = response[ "CreateAccountStatus" ]
		
		@staticmethod
		def _get_assume_role_credentials( aws_account_id, session_lifetime ):
			# Generate ARN for the sub-account AWS administrator role
			sub_account_admin_role_arn = "arn:aws:iam::" + str( aws_account_id ) + ":role/" + os.environ.get( "customer_aws_admin_assume_role" )
			
			# Session lifetime must be a minimum of 15 minutes
			# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html#STS.Client.assume_role
			min_session_lifetime_seconds = 900
			if session_lifetime < min_session_lifetime_seconds:
				session_lifetime = min_session_lifetime_seconds
			
			role_session_name = "Refinery-Managed-Account-Support-" + get_urand_password( 12 )
			
			response = STS_CLIENT.assume_role(
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
		def _create_new_console_user( access_key_id, secret_access_key, session_token, username, password ):
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
				PolicyDocument=json.dumps( CUSTOMER_IAM_POLICY ),
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
		def create_new_sub_aws_account( self, account_type, aws_account_id ):
			return TaskSpawner._create_new_sub_aws_account(
				account_type,
				aws_account_id
			)
			
		@staticmethod
		def _create_new_sub_aws_account( account_type, aws_account_id ):
			# Create a unique ID for the Refinery AWS account
			aws_unique_account_id = get_urand_password( 16 ).lower()
			
			# Store the AWS account in the database
			new_aws_account = AWSAccount()
			new_aws_account.account_label = ""
			new_aws_account.region = os.environ.get( "region_name" )
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
			new_aws_account.aws_account_email = os.environ.get( "customer_aws_email_prefix" ) + aws_unique_account_id + os.environ.get( "customer_aws_email_suffix" )
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
			
			while True:
				logit( "Attempting to assume the sub-account's administrator role..." )
				
				try:
					# We then assume the administrator role for the sub-account we created
					assumed_role_credentials = TaskSpawner._get_assume_role_credentials(
						str( new_aws_account.account_id ),
						3600 # One hour - TODO CHANGEME
					)
					break
				except botocore.exceptions.ClientError as boto_error:
					print( boto_error )
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
				assumed_role_credentials[ "access_key_id" ],
				assumed_role_credentials[ "secret_access_key" ],
				assumed_role_credentials[ "session_token" ],
				str( new_aws_account.iam_admin_username ),
				str( new_aws_account.iam_admin_password )
			)
			
			# Add AWS account to database
			dbsession = DBSession()
			dbsession.add( new_aws_account )
			dbsession.commit()
			dbsession.close()
			
			logit( "New AWS account created successfully and stored in database as 'CREATED'!" )
			
			return True
			
		@run_on_executor
		def terraform_configure_aws_account( self, aws_account_dict ):
			return TaskSpawner._terraform_configure_aws_account(
				aws_account_dict
			)
			
		@run_on_executor
		def write_terraform_base_files( self, aws_account_dict ):
			return TaskSpawner._write_terraform_base_files(
				aws_account_dict
			)
			
		@staticmethod
		def _write_terraform_base_files( aws_account_dict ):
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
		def __write_terraform_base_files( aws_account_data, base_dir ):
			logit( "Setting up the base Terraform files (AWS Acc. ID '" + aws_account_data[ "account_id" ] + "')..." )
			
			# Get some temporary assume role credentials for the account
			assumed_role_credentials = TaskSpawner._get_assume_role_credentials(
				str( aws_account_data[ "account_id" ] ),
				3600 # One hour - TODO CHANGEME
			)
			
			sub_account_admin_role_arn = "arn:aws:iam::" + str( aws_account_data[ "account_id" ] ) + ":role/" + os.environ.get( "customer_aws_admin_assume_role" )
			
			# Write out the terraform configuration data
			terraform_configuration_data = {
				"session_token": assumed_role_credentials[ "session_token" ],
				"role_session_name": assumed_role_credentials[ "role_session_name" ],
				"assume_role_arn": sub_account_admin_role_arn,
				"access_key": assumed_role_credentials[ "access_key_id" ],
				"secret_key": assumed_role_credentials[ "secret_access_key" ],
				"region": os.environ.get( "region_name" ),
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
		def terraform_apply( self, aws_account_data ):
			"""
			This applies the latest terraform config to an account.
			
			THIS IS DANGEROUS, MAKE SURE YOU DID A FLEET TERRAFORM PLAN
			FIRST. NO EXCUSES, THIS IS ONE OF THE FEW WAYS TO BREAK PROD
			FOR OUR CUSTOMERS.
			
			-mandatory
			"""
			return TaskSpawner._terraform_apply(
				aws_account_data
			)
		
		@staticmethod
		def _terraform_apply( aws_account_data ):
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
				aws_account_data
			)
			temporary_directory = terraform_configuration_data[ "base_dir" ]
			
			try:
				logit( "Performing 'terraform apply' to AWS Account " + aws_account_data[ "account_id" ] + "..." )
				
				# Terraform plan
				process_handler = subprocess.Popen(
					[
						temporary_directory + "terraform",
						"apply",
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
					TaskSpawner.send_terraform_provisioning_error(
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
		def terraform_plan( self, aws_account_data ):
			"""
			This does a terraform plan to an account and sends an email
			with the results. This allows us to see the impact of a new
			terraform change before we roll it out across our customer's
			AWS accounts.
			"""
			return TaskSpawner._terraform_plan(
				aws_account_data
			)
		
		@staticmethod
		def _terraform_plan( aws_account_data ):
			terraform_configuration_data = TaskSpawner._write_terraform_base_files(
				aws_account_data
			)
			temporary_directory = terraform_configuration_data[ "base_dir" ]
			
			try:
				logit( "Performing 'terraform plan' to AWS account " + aws_account_data[ "account_id" ] + "..." )
				
				# Terraform plan
				process_handler = subprocess.Popen(
					[
						temporary_directory + "terraform",
						"plan",
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
		def _terraform_configure_aws_account( aws_account_data ):
			terraform_configuration_data = TaskSpawner._write_terraform_base_files(
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
					TaskSpawner.send_terraform_provisioning_error(
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
		def unfreeze_aws_account( self, credentials ):
			return TaskSpawner._unfreeze_aws_account(
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
			lambda_arns = TaskSpawner.get_lambda_arns(
				credentials
			)
			
			# Remove function throttle from each Lambda
			for lambda_arn in lambda_arns:
				lambda_client.delete_function_concurrency(
					FunctionName=lambda_arn
				)
			
			# Start EC2 instance(s)
			ec2_instance_ids = TaskSpawner.get_ec2_instance_ids( credentials )
			
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

			# Iterate over list of Lambda ARNs and set concurrency to zero for all
			for lambda_arn in lambda_arn_list:
				lambda_client.put_function_concurrency(
					FunctionName=lambda_arn,
					ReservedConcurrentExecutions=0
				)
				
			return lambda_arn_list
			
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
			
		@run_on_executor
		def freeze_aws_account( self, credentials ):
			return TaskSpawner._freeze_aws_account( credentials )
		
		@staticmethod
		def _freeze_aws_account( credentials ):
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
			
			iam_client = get_aws_client(
				"iam",
				credentials
			)
			
			lambda_client = get_aws_client(
				"lambda",
				credentials
			)
			
			codebuild_client = get_aws_client(
				"codebuild",
				credentials
			)
			
			ec2_client = get_aws_client(
				"ec2",
				credentials
			)
			
			# Rotate and log out users from the AWS console
			new_console_user_password = TaskSpawner._recreate_aws_console_account(
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
			
			# Get Lambda ARNs
			lambda_arn_list = TaskSpawner.get_lambda_arns( credentials )
			
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
				
			ec2_instance_ids = TaskSpawner.get_ec2_instance_ids( credentials )

			stop_instance_response = ec2_client.stop_instances(
				InstanceIds=ec2_instance_ids
			)
			
			dbsession.close()
			return False
			
		@run_on_executor
		def recreate_aws_console_account( self, credentials, rotate_password ):
			return TaskSpawner._recreate_aws_console_account(
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
		def send_email( self, to_email_string, subject_string, message_text_string, message_html_string ):
			"""
			to_email_string: "example@refinery.io"
			subject_string: "Your important email"
			message_text_string: "You have an important email here!"
			message_html_string: "<h1>ITS IMPORTANT AF!</h1>"
			"""
			return TaskSpawner._send_email(
				to_email_string,
				subject_string,
				message_text_string,
				message_html_string
			)
			
		@staticmethod
		def _send_email( to_email_string, subject_string, message_text_string, message_html_string ):
			logit( "Sending email to '" + to_email_string + "' with subject '" + subject_string + "'..." )
			
			requests_options = {
				"auth": ( "api", os.environ.get( "mailgun_api_key" ) ),
				"data": {
					"from": os.environ.get( "from_email" ),
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
		def send_terraform_provisioning_error( aws_account_id, error_output ):
			TaskSpawner._send_email(
				os.environ.get( "alerts_email" ),
				"[AWS Account Provisioning Error] The Refinery AWS Account #" + aws_account_id + " Encountered a Fatal Error During Terraform Provisioning",
				pystache.render(
					EMAIL_TEMPLATES[ "terraform_provisioning_error_alert" ],
					{
						"aws_account_id": aws_account_id,
						"error_output": error_output,
					}
				),
				False,
			)
			
		@staticmethod
		def send_account_freeze_email( aws_account_id, amount_accumulated, organization_admin_email ):
			TaskSpawner._send_email(
				os.environ.get( "alerts_email" ),
				"[Freeze Alert] The Refinery AWS Account #" + aws_account_id + " has been frozen for going over its account limit!",
				False,
				pystache.render(
					EMAIL_TEMPLATES[ "account_frozen_alert" ],
					{
						"aws_account_id": aws_account_id,
						"free_trial_billing_limit": os.environ.get( "free_trial_billing_limit" ),
						"amount_accumulated": amount_accumulated,
						"organization_admin_email": organization_admin_email,
					}
				),
			)
		
		@run_on_executor
		def send_registration_confirmation_email( self, email_address, auth_token ):
			registration_confirmation_link = os.environ.get( "web_origin" ) + "/authentication/email/" + auth_token
			
			TaskSpawner._send_email(
				email_address,
				"Refinery.io - Confirm your Refinery registration",
				pystache.render(
					EMAIL_TEMPLATES[ "registration_confirmation_text" ],
					{
						"registration_confirmation_link": registration_confirmation_link,
					}
				),
				pystache.render(
					EMAIL_TEMPLATES[ "registration_confirmation" ],
					{
						"registration_confirmation_link": registration_confirmation_link,
					}
				),
			)
			
		@run_on_executor
		def send_internal_registration_confirmation_email( self, customer_email_address, customer_name, customer_phone ):
			TaskSpawner._send_email(
				os.environ.get( "internal_signup_notification_email" ),
				"Refinery User Signup, " + customer_email_address,
				pystache.render(
					EMAIL_TEMPLATES[ "internal_registration_notification_text" ],
					{
						"customer_email_address": customer_email_address,
						"customer_name": customer_name,
						"customer_phone": customer_phone
					}
				),
				pystache.render(
					EMAIL_TEMPLATES[ "internal_registration_notification" ],
					{
						"customer_email_address": customer_email_address,
						"customer_name": customer_name,
						"customer_phone": customer_phone
					}
				),
			)
	
		@run_on_executor
		def send_authentication_email( self, email_address, auth_token ):
			authentication_link = os.environ.get( "web_origin" ) + "/authentication/email/" + auth_token
			
			TaskSpawner._send_email(
				email_address,
				"Refinery.io - Login by email confirmation",
				pystache.render(
					EMAIL_TEMPLATES[ "authentication_email_text" ],
					{
						"email_authentication_link": authentication_link,
					}
				),
				pystache.render(
					EMAIL_TEMPLATES[ "authentication_email" ],
					{
						"email_authentication_link": authentication_link,
					}
				),
			)

		@run_on_executor
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
		def associate_card_token_with_customer_account( self, stripe_customer_id, card_token ):
			# Add the card to the customer's account.
			new_card = stripe.Customer.create_source(
				stripe_customer_id,
				source=card_token
			)
			
			return new_card[ "id" ]
			
		@run_on_executor
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
		def get_stripe_customer_information( self, stripe_customer_id ):
			return TaskSpawner._get_stripe_customer_information( stripe_customer_id )
			
		@staticmethod
		def _get_stripe_customer_information( stripe_customer_id ):
			return stripe.Customer.retrieve(
				stripe_customer_id
			)
			
		@run_on_executor
		def set_stripe_customer_default_payment_source( self, stripe_customer_id, card_id ):
			customer_update_response = stripe.Customer.modify(
				stripe_customer_id,
				default_source=card_id,
			)
			
			logit( customer_update_response )
			
		@run_on_executor
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
			dbsession = DBSession()
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
				os.environ.get( "stripe_finalize_invoices" )
			)
			
			# Iterate over each organization
			for organization_id in organization_ids:
				dbsession = DBSession()
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
				os.environ.get( "billing_alert_email" ),
				"[URGENT][IMPORTANT]: Monthly customer invoice generation has completed. One hour to auto-finalization.",
				False,
				"The monthly Stripe invoice generation has completed. You have <b>one hour</b> to review invoices before they go out to customers.<br /><a href=\"https://dashboard.stripe.com/invoices\"><b>Click here to review the generated invoices</b></a><br /><br />",
			)

		@run_on_executor
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
			
			while True:
				ce_response = COST_EXPLORER.get_cost_and_usage(
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
		def enforce_account_limits( self, aws_account_running_cost_list ):
			"""
			{
				"aws_account_id": "00000000000",
				"billing_total": "12.39",
				"unit": "USD",
			}
			"""
			dbsession = DBSession()
			
			# Pull the configured free trial account limits
			free_trial_user_max_amount = float( os.environ.get( "free_trial_billing_limit" ) )
			
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
				if aws_account == None:
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
						aws_account.to_dict()
					)
					
					# Send account frozen email to us to know that it happened
					TaskSpawner.send_account_freeze_email(
						aws_account_info[ "aws_account_id" ],
						aws_account_info[ "billing_total" ],
						owner_organization.billing_admin_user.email
					)
					
			dbsession.close()
	
		@run_on_executor
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
				account_id,
				account_type,
				billing_start_date,
				billing_end_date,
				"monthly",
				use_cache
			)
			
		@staticmethod
		def _get_sub_account_billing_data( account_id, account_type, start_date, end_date, granularity, use_cache ):
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
			
			# Markup multiplier
			markup_multiplier = 1 + ( int( os.environ.get( "mark_up_percent" ) ) / 100 )
			
			# Check if this is the first billing month
			is_first_account_billing_month = is_organization_first_month(
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
		def _get_sub_account_service_breakdown_list( account_id, account_type, start_date, end_date, granularity, use_cache ):
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
			dbsession = DBSession()
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
		def _api_get_sub_account_billing_data( account_id, account_type, start_date, end_date, granularity ):
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

			if account_type == "MANAGED":
				and_statements.append({
					"Dimensions": {
						"Key": "LINKED_ACCOUNT",
						"Values": [
							str( account_id )
						]
					}
				})
				billing_client = COST_EXPLORER
			elif account_type == "THIRDPARTY":
				# For third party we need to do an assume role into the account
				dbsession = DBSession()
				aws_account = dbsession.query( AWSAccount ).filter_by(
					account_id=account_id
				).first()
				aws_account_dict = aws_account.to_dict()
				dbsession.close()

				billing_client = get_aws_client(
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
					os.environ.get( "alerts_email" ),
					"[Billing Notification] The Refinery AWS Account #" + account_id + " Encountered An Error When Calculating the Bill",
					"See HTML email.",
					pystache.render(
						EMAIL_TEMPLATES[ "billing_error_email" ],
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
		def get_sub_account_billing_forecast( self, account_id, start_date, end_date, granularity ):
			"""
			account_id: 994344292413
			start_date: 2017-05-01
			end_date: 2017-06-01
			granularity: monthly"
			"""
			metric_name = "NET_UNBLENDED_COST"
			
			# Markup multiplier
			markup_multiplier = 1 + ( int( os.environ.get( "mark_up_percent" ) ) / 100 )
			
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
			
			response = COST_EXPLORER.get_cost_forecast(
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
		def check_if_layer_exists( self, credentials, layer_name ):
			lambda_client = get_aws_client( "lambda", credentials )
			
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
		def create_lambda_layer( self, credentials, layer_name, description, s3_bucket, s3_object_key ):
			lambda_client = get_aws_client( "lambda", credentials )
			
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
		def warm_up_lambda( self, credentials, arn, warmup_concurrency_level ):
			lambda_client = get_aws_client(
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
		def execute_aws_lambda( self, credentials, arn, input_data ):
			return TaskSpawner._execute_aws_lambda( credentials, arn, input_data )
		
		@staticmethod
		def _execute_aws_lambda( credentials, arn, input_data ):
			lambda_client = get_aws_client( "lambda", credentials )
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
			if( "START RequestId: " in log_output and "END RequestId: " in log_output ):
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
		def delete_aws_lambda( self, credentials, arn_or_name ):
			return TaskSpawner._delete_aws_lambda( credentials, arn_or_name )
		
		@staticmethod
		def _delete_aws_lambda( credentials, arn_or_name ):
			lambda_client = get_aws_client( "lambda", credentials )
			return lambda_client.delete_function(
				FunctionName=arn_or_name
			)
			
		@run_on_executor
		def update_lambda_environment_variables( self, credentials, func_name, environment_variables ):
			lambda_client = get_aws_client( "lambda", credentials )
			
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
		def build_lambda( credentials, lambda_object ):
			logit( "Building Lambda " + lambda_object.language + " with libraries: " + str( lambda_object.libraries ), "info" )
			if not ( lambda_object.language in LAMBDA_SUPPORTED_LANGUAGES ):
				raise Exception( "Error, this language '" + language + "' is not yet supported by refinery!" )
			
			if lambda_object.language == "python2.7":
				package_zip_data = TaskSpawner._build_python27_lambda(
					credentials,
					lambda_object.code,
					lambda_object.libraries
				)
			elif lambda_object.language == "python3.6":
				package_zip_data = TaskSpawner._build_python36_lambda(
					credentials,
					lambda_object.code,
					lambda_object.libraries
				)
			elif lambda_object.language == "php7.3":
				package_zip_data = TaskSpawner._build_php_73_lambda(
					credentials,
					lambda_object.code,
					lambda_object.libraries
				)
			elif lambda_object.language == "nodejs8.10":
				package_zip_data = TaskSpawner._build_nodejs_810_lambda(
					credentials,
					lambda_object.code,
					lambda_object.libraries
				)
			elif lambda_object.language == "nodejs10.16.3":
				package_zip_data = TaskSpawner._build_nodejs_10163_lambda(
					credentials,
					lambda_object.code,
					lambda_object.libraries
				)
			elif lambda_object.language == "go1.12":
				package_zip_data = TaskSpawner.get_go112_zip(
					credentials,
					lambda_object.code
				)
			elif lambda_object.language == "ruby2.6.4":
				package_zip_data = TaskSpawner._build_ruby_264_lambda(
					credentials,
					lambda_object.code,
					lambda_object.libraries
				)

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
		def set_lambda_reserved_concurrency( self, credentials, arn, reserved_concurrency_count ):
			# Create Lambda client
			lambda_client = get_aws_client(
				"lambda",
				credentials
			)
			
			set_concurrency_response = lambda_client.put_function_concurrency(
				FunctionName=arn,
				ReservedConcurrentExecutions=int( reserved_concurrency_count )
			)
			
		@run_on_executor
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
			s3_client = get_aws_client(
				"s3",
				credentials
			)
			
			# Check if we've already deployed this exact same Lambda before
			already_exists = TaskSpawner._s3_object_exists(
				credentials,
				credentials[ "lambda_packages_bucket" ],
				s3_package_zip_path
			)
			
			if not already_exists:
				# Build the Lambda package .zip and return the zip data for it
				lambda_zip_package_data = TaskSpawner.build_lambda(
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
				credentials,
				lambda_object,
				s3_package_zip_path,
			)
			
			# If it's an inline execution we can cache the
			# built Lambda and re-used it for future executions
			# that share the same configuration when run.
			if lambda_object.is_inline_execution and not ( lambda_object.language in NOT_SUPPORTED_INLINE_EXECUTION_LANGUAGES ):
				logit( "Caching inline execution to speed up future runs..." )
				TaskSpawner._cache_inline_lambda_execution(
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
		def _get_cached_inline_execution_lambda_entries( credentials ):
			# Check how many inline execution Lambdas we already have
			# saved in AWS. If it's too many we need to clean up!
			# Get the oldest saved inline execution from the stack and
			# delete it from AWS. This way we don't fill up the 75GB
			# per-account limitation!
			dbsession = DBSession()
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
			
			logit( "Number of existing Lambdas cached for inline executions: " + str( len( existing_inline_execution_lambdas_objects ) ) )
			
			return existing_inline_execution_lambdas
			
		@staticmethod
		def _delete_cached_inline_execution_lambda( credentials, arn, lambda_uuid ):
			lambda_manager._delete_lambda(
				credentials,
				False,
				False,
				False,
				arn
			)
			
			# Delete the Lambda from the database now that we've
			# deleted it from AWS.
			dbsession = DBSession()
			dbsession.query( InlineExecutionLambda ).filter_by(
				id=lambda_uuid
			).delete()
			dbsession.commit()
			dbsession.close()
			
		@staticmethod
		def _add_inline_execution_lambda_entry( credentials, inline_execution_hash_key, arn, lambda_size ):
			# Add Lambda to inline execution database so we know we can
			# re-use it at a later time.
			dbsession = DBSession()
			inline_execution_lambda = InlineExecutionLambda()
			inline_execution_lambda.unique_hash_key = inline_execution_hash_key
			inline_execution_lambda.arn = arn
			inline_execution_lambda.size = lambda_size
			inline_execution_lambda.aws_account_id = credentials[ "id" ]
			dbsession.add( inline_execution_lambda )
			dbsession.commit()
			dbsession.close()
			
		@staticmethod
		def _cache_inline_lambda_execution( credentials, language, timeout, memory, environment_variables, layers, libraries, arn, lambda_size ):
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
				credentials
			)
			
			if existing_inline_execution_lambdas and len( existing_inline_execution_lambdas ) > max_number_of_inline_execution_lambdas:
				number_of_lambdas_to_delete = len( existing_inline_execution_lambdas ) - max_number_of_inline_execution_lambdas
				
				logit( "Deleting #" + str( number_of_lambdas_to_delete ) + " old cached inline execution Lambda(s) from AWS..." )
				
				lambdas_to_delete = existing_inline_execution_lambdas[:number_of_lambdas_to_delete]
			
				for lambda_to_delete in lambdas_to_delete:
					logit( "Deleting '" + lambda_to_delete[ "arn" ] + "' from AWS..." )
					
					TaskSpawner._delete_cached_inline_execution_lambda(
						credentials,
						lambda_to_delete[ "arn" ],
						lambda_to_delete[ "id" ]
					)
			
			TaskSpawner._add_inline_execution_lambda_entry(
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
				"layers": lambda_layers,
				"libraries": libraries
			}
			
			hash_key = hashlib.sha256(
				json.dumps(
					hash_dict,
					sort_keys=True
				)
			).hexdigest()
			
			return hash_key
		
		@staticmethod
		def _deploy_aws_lambda( credentials, lambda_object, s3_package_zip_path ):
			# Generate environment variables data structure
			env_data = {}
			for env_pair in lambda_object.environment_variables:
				env_data[ env_pair[ "key" ] ] = env_pair[ "value" ]
				
			# Create Lambda client
			lambda_client = get_aws_client(
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
						credentials,
						lambda_object.name
					)
					
					# Now create it since we're clear
					return TaskSpawner._deploy_aws_lambda(
						credentials,
						lambda_object,
						s3_package_zip_path
					)
				raise
			
			return response
		
		@run_on_executor
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
		def get_python36_lambda_base_zip( credentials, libraries ):
			s3_client = get_aws_client(
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
			
			if TaskSpawner._s3_object_exists( credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
				return TaskSpawner._read_from_s3(
					credentials,
					credentials[ "lambda_packages_bucket" ],
					final_s3_package_zip_path
				)
			
			# Kick off CodeBuild for the libraries to get a zip artifact of
			# all of the libraries.
			build_id = TaskSpawner._start_python36_codebuild(
				credentials,
				libraries_object
			)
			
			# This continually polls for the CodeBuild build to finish
			# Once it does it returns the raw artifact zip data.
			return TaskSpawner._get_codebuild_artifact_zip_data(
				credentials,
				build_id,
				final_s3_package_zip_path
			)
			
		@staticmethod
		def get_python27_lambda_base_zip( credentials, libraries ):
			s3_client = get_aws_client(
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
			
			if TaskSpawner._s3_object_exists( credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
				return TaskSpawner._read_from_s3(
					credentials,
					credentials[ "lambda_packages_bucket" ],
					final_s3_package_zip_path
				)
			
			# Kick off CodeBuild for the libraries to get a zip artifact of
			# all of the libraries.
			build_id = TaskSpawner._start_python27_codebuild(
				credentials,
				libraries_object
			)
			
			# This continually polls for the CodeBuild build to finish
			# Once it does it returns the raw artifact zip data.
			return TaskSpawner._get_codebuild_artifact_zip_data(
				credentials,
				build_id,
				final_s3_package_zip_path
			)
			
		@staticmethod
		def get_go112_zip( credentials, code ):
			# Kick off CodeBuild
			build_id = TaskSpawner.start_go112_codebuild(
				credentials,
				code
			)
			
			# Since go doesn't have the traditional libraries
			# files like requirements.txt or package.json we
			# just use the code as a hash here.
			libraries_object = { "code": code }
			
			final_s3_package_zip_path = TaskSpawner._get_final_zip_package_path(
				"go1.12",
				libraries_object
			)
			
			if TaskSpawner._s3_object_exists( credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
				return TaskSpawner._read_from_s3(
					credentials,
					credentials[ "lambda_packages_bucket" ],
					final_s3_package_zip_path
				)
			
			# This continually polls for the CodeBuild build to finish
			# Once it does it returns the raw artifact zip data.
			return TaskSpawner._get_codebuild_artifact_zip_data(
				credentials,
				build_id,
				final_s3_package_zip_path
			)
			
		@staticmethod
		def start_go112_codebuild( credentials, code ):
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "go1.12" ]
			
			codebuild_client = get_aws_client(
				"codebuild",
				credentials
			)
			
			s3_client = get_aws_client(
				"s3",
				credentials
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
						"commands": [
							"export GOPATH=\"$(pwd)\"",
							"export GOBIN=$GOPATH/bin",
							"go get",
							"go build lambda.go"
						]
					},
					"install": {
						"runtime-versions": {
							"golang": 1.12
						}
					}
				},
				"run-as": "root",
				"version": 0.2
			}
			
			empty_folders = [
				"bin",
				"pkg",
				"src"
			]
			
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
				
				# Write the main.go file
				main_go_file = zipfile.ZipInfo(
					"lambda.go"
				)
				main_go_file.external_attr = 0777 << 16L
				zip_file_handler.writestr(
					main_go_file,
					str( code )
				)
				
				# Create empty folders for bin, pkg, and src
				for empty_folder in empty_folders:
					blank_file = zipfile.ZipInfo(
						empty_folder + "/blank"
					)
					blank_file.external_attr = 0777 << 16L
					zip_file_handler.writestr(
						blank_file,
						""
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
		def start_python36_codebuild( self, credentials, libraries_object ):
			return TaskSpawner._start_python36_codebuild( credentials, libraries_object )
			
		@staticmethod
		def _start_python36_codebuild( credentials, libraries_object ):
			"""
			Returns a build ID to be polled at a later time
			"""
			codebuild_client = get_aws_client(
				"codebuild",
				credentials
			)
			
			s3_client = get_aws_client(
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
		def start_python27_codebuild( self, credentials, libraries_object ):
			return TaskSpawner._start_python27_codebuild( credentials, libraries_object )
			
		@staticmethod
		def _start_python27_codebuild( credentials, libraries_object ):
			"""
			Returns a build ID to be polled at a later time
			"""
			codebuild_client = get_aws_client(
				"codebuild",
				credentials
			)
			
			s3_client = get_aws_client(
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
		def start_ruby264_codebuild( self, credentials, libraries_object ):
			return TaskSpawner._start_ruby264_codebuild( credentials, libraries_object )
			
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
		def _start_ruby264_codebuild( credentials, libraries_object ):
			"""
			Returns a build ID to be polled at a later time
			"""
			codebuild_client = get_aws_client(
				"codebuild",
				credentials
			)
			
			s3_client = get_aws_client(
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
		def start_node810_codebuild( self, credentials, libraries_object ):
			return TaskSpawner._start_node810_codebuild( credentials, libraries_object )
			
		@staticmethod
		def _start_node810_codebuild( credentials, libraries_object ):
			"""
			Returns a build ID to be polled at a later time
			"""
			codebuild_client = get_aws_client(
				"codebuild",
				credentials
			)
			
			s3_client = get_aws_client(
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
		def s3_object_exists( self, credentials, bucket_name, object_key ):
			return TaskSpawner._s3_object_exists(
				credentials,
				bucket_name,
				object_key
			)
			
		@staticmethod
		def _s3_object_exists( credentials, bucket_name, object_key ):
			s3_client = get_aws_client(
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
		def get_ruby_264_lambda_base_zip( credentials, libraries ):
			s3_client = get_aws_client(
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
			
			if TaskSpawner._s3_object_exists( credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
				return TaskSpawner._read_from_s3(
					credentials,
					credentials[ "lambda_packages_bucket" ],
					final_s3_package_zip_path
				)
			
			# Kick off CodeBuild for the libraries to get a zip artifact of
			# all of the libraries.
			build_id = TaskSpawner._start_ruby264_codebuild(
				credentials,
				libraries_object
			)
			
			# This continually polls for the CodeBuild build to finish
			# Once it does it returns the raw artifact zip data.
			return TaskSpawner._get_codebuild_artifact_zip_data(
				credentials,
				build_id,
				final_s3_package_zip_path
			)
		
		@staticmethod
		def get_nodejs_810_lambda_base_zip( credentials, libraries ):
			s3_client = get_aws_client(
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
			
			if TaskSpawner._s3_object_exists( credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
				return TaskSpawner._read_from_s3(
					credentials,
					credentials[ "lambda_packages_bucket" ],
					final_s3_package_zip_path
				)
			
			# Kick off CodeBuild for the libraries to get a zip artifact of
			# all of the libraries.
			build_id = TaskSpawner._start_node810_codebuild(
				credentials,
				libraries_object
			)
			
			# This continually polls for the CodeBuild build to finish
			# Once it does it returns the raw artifact zip data.
			return TaskSpawner._get_codebuild_artifact_zip_data(
				credentials,
				build_id,
				final_s3_package_zip_path
			)
		
		@run_on_executor
		def get_codebuild_artifact_zip_data( self, credentials, build_id, final_s3_package_zip_path ):
			return TaskSpawner._get_codebuild_artifact_zip_data(
				credentials,
				build_id,
				final_s3_package_zip_path
			)
		
		@staticmethod
		def _get_codebuild_artifact_zip_data( credentials, build_id, final_s3_package_zip_path ):
			s3_client = get_aws_client(
				"s3",
				credentials
			)
			
			# Wait until the codebuild is finished
			# This is pieced out so that we can also kick off codebuilds
			# without having to pull the final zip result
			TaskSpawner._finalize_codebuild(
				credentials,
				build_id,
				final_s3_package_zip_path
			)
			
			return TaskSpawner._read_from_s3(
				credentials,
				credentials[ "lambda_packages_bucket" ],
				final_s3_package_zip_path
			)
			
		@run_on_executor
		def finalize_codebuild( self, credentials, build_id, final_s3_package_zip_path ):
			return TaskSpawner._finalize_codebuild(
				credentials,
				build_id,
				final_s3_package_zip_path
			)
			
		@staticmethod
		def _finalize_codebuild( credentials, build_id, final_s3_package_zip_path ):
			codebuild_client = get_aws_client(
				"codebuild",
				credentials
			)
			
			s3_client = get_aws_client(
				"s3",
				credentials
			)
			
			build_info = {}
			
			# Generate output artifact location from the build ID
			build_id_parts = build_id.split( ":" )
			output_artifact_path = build_id_parts[1] + "/package.zip"
			
			# Loop until we have the build information
			while True:
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
					credentials,
					log_group_name,
					log_stream_name
				)
				
				raise BuildException({
					"msg": "Build ID " + build_id + " failed with status code '" + build_status + "'!",
					"build_output": log_output,
				})
			
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
		def get_php73_lambda_base_zip( credentials, libraries ):
			s3_client = get_aws_client(
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
			
			if TaskSpawner._s3_object_exists( credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
				return TaskSpawner._read_from_s3(
					credentials,
					credentials[ "lambda_packages_bucket" ],
					final_s3_package_zip_path
				)
			
			# Kick off CodeBuild for the libraries to get a zip artifact of
			# all of the libraries.
			build_id = TaskSpawner._start_php73_codebuild(
				credentials,
				libraries_object
			)
			
			# This continually polls for the CodeBuild build to finish
			# Once it does it returns the raw artifact zip data.
			return TaskSpawner._get_codebuild_artifact_zip_data(
				credentials,
				build_id,
				final_s3_package_zip_path
			)

		@run_on_executor
		def start_php73_codebuild( self, credentials, libraries_object ):
			return TaskSpawner._start_php73_codebuild( credentials, libraries_object )

		@staticmethod
		def _start_php73_codebuild( credentials, libraries_object ):
			"""
			Returns a build ID to be polled at a later time
			"""
			codebuild_client = get_aws_client(
				"codebuild",
				credentials
			)
			
			s3_client = get_aws_client(
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
		def _get_php_73_base_code( code ):
			code = re.sub(
				r"function main\([^\)]+\)[^{]\{",
				"function main( $block_input ) {global $backpack;",
				code
			)
			
			code = code.replace(
				"require __DIR__",
				"require $_ENV[\"LAMBDA_TASK_ROOT\"]"
			)
			
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "php7.3" ]
			return code
			
		@staticmethod
		def _build_php_73_lambda( credentials, code, libraries ):
			code = TaskSpawner._get_php_73_base_code(
				code
			)
			
			# Use CodeBuilder to get a base zip of the libraries
			base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
			if len( libraries ) > 0:
				base_zip_data = TaskSpawner.get_php73_lambda_base_zip(
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
		def _get_ruby_264_base_code( code ):
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "ruby2.6.4" ]
			return code
			
		@staticmethod
		def _build_ruby_264_lambda( credentials, code, libraries ):
			code = TaskSpawner._get_ruby_264_base_code(
				code
			)
			
			# Use CodeBuilder to get a base zip of the libraries
			base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
			
			if len( libraries ) > 0:
				base_zip_data = TaskSpawner.get_ruby_264_lambda_base_zip(
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
		def _get_nodejs_10163_base_code( code ):
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
			
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "nodejs10.16.3" ]
			return code
			
		@staticmethod
		def _build_nodejs_10163_lambda( credentials, code, libraries ):
			code = TaskSpawner._get_nodejs_10163_base_code(
				code
			)
			
			# Use CodeBuilder to get a base zip of the libraries
			base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
			if len( libraries ) > 0:
				base_zip_data = TaskSpawner.get_nodejs_10163_lambda_base_zip(
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
		def get_nodejs_10163_lambda_base_zip( credentials, libraries ):
			s3_client = get_aws_client(
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
			
			if TaskSpawner._s3_object_exists( credentials, credentials[ "lambda_packages_bucket" ], final_s3_package_zip_path ):
				return TaskSpawner._read_from_s3(
					credentials,
					credentials[ "lambda_packages_bucket" ],
					final_s3_package_zip_path
				)
			
			# Kick off CodeBuild for the libraries to get a zip artifact of
			# all of the libraries.
			build_id = TaskSpawner._start_node10163_codebuild(
				credentials,
				libraries_object
			)
			
			# This continually polls for the CodeBuild build to finish
			# Once it does it returns the raw artifact zip data.
			return TaskSpawner._get_codebuild_artifact_zip_data(
				credentials,
				build_id,
				final_s3_package_zip_path
			)
			
		@run_on_executor
		def start_node10163_codebuild( self, credentials, libraries_object ):
			return TaskSpawner._start_node810_codebuild( credentials, libraries_object )
			
		@staticmethod
		def _start_node10163_codebuild( credentials, libraries_object ):
			"""
			Returns a build ID to be polled at a later time
			"""
			codebuild_client = get_aws_client(
				"codebuild",
				credentials
			)
			
			s3_client = get_aws_client(
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
		def _get_nodejs_810_base_code( code ):
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
			
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "nodejs8.10" ]
			return code
			
		@staticmethod
		def _build_nodejs_810_lambda( credentials, code, libraries ):
			code = TaskSpawner._get_nodejs_810_base_code(
				code
			)
			
			# Use CodeBuilder to get a base zip of the libraries
			base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
			if len( libraries ) > 0:
				base_zip_data = TaskSpawner.get_nodejs_810_lambda_base_zip(
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
		def _get_python36_base_code( code ):
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "python3.6" ]
			return code
			
		@staticmethod
		def _build_python36_lambda( credentials, code, libraries ):
			code = TaskSpawner._get_python36_base_code(
				code
			)
					
			base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
			if len( libraries ) > 0:
				base_zip_data = TaskSpawner.get_python36_lambda_base_zip(
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
		def _get_python27_base_code( code ):
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "python2.7" ]
			return code
		
		@staticmethod
		def _build_python27_lambda( credentials, code, libraries ):
			"""
			Build Lambda package zip and return zip data
			"""
			
			"""
			Inject base libraries (e.g. redis) into lambda
			and the init code.
			"""

			# Get customized base code
			code = TaskSpawner._get_python27_base_code(
				code
			)
					
			base_zip_data = copy.deepcopy( EMPTY_ZIP_DATA )
			if len( libraries ) > 0:
				base_zip_data = TaskSpawner.get_python27_lambda_base_zip(
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
		def automatically_fix_schedule_expression( schedule_expression ):
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
		def create_cloudwatch_group( self, credentials, group_name, tags_dict, retention_days ):
			# Create S3 client
			cloudwatch_logs = get_aws_client(
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
		def create_cloudwatch_rule( self, credentials, id, name, schedule_expression, description, input_string ):
			events_client = get_aws_client(
				"events",
				credentials,
			)
			
			schedule_expression = TaskSpawner.automatically_fix_schedule_expression( schedule_expression )
			
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
		def add_rule_target( self, credentials, rule_name, target_id, target_arn, input_string ):
			# Automatically parse JSON
			try:
				input_string = json.loads(
					input_string
				)
			except:
				pass
			
			events_client = get_aws_client(
				"events",
				credentials,
			)
			
			lambda_client = get_aws_client(
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
				#SourceAccount=os.environ.get( "aws_account_id" ) # THIS IS A BUG IN AWS NEVER PASS THIS
			)
			
			return rule_creation_response
		
		@run_on_executor
		def create_sns_topic( self, credentials, id, topic_name ):
			sns_client = get_aws_client(
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
		def subscribe_lambda_to_sns_topic( self, credentials, topic_arn, lambda_arn ):
			"""
			For AWS Lambda you need to add a permission to the Lambda function itself
			via the add_permission API call to allow invocation via the SNS event.
			"""
			lambda_client = get_aws_client(
				"lambda",
				credentials
			)
			
			sns_client = get_aws_client(
				"sns",
				credentials,
			)
			
			lambda_permission_add_response = lambda_client.add_permission(
				FunctionName=lambda_arn,
				StatementId=str( uuid.uuid4() ),
				Action="lambda:*",
				Principal="sns.amazonaws.com",
				SourceArn=topic_arn,
				#SourceAccount=os.environ.get( "aws_account_id" ) # THIS IS A BUG IN AWS NEVER PASS THIS
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
		def create_sqs_queue( self, credentials, id, queue_name, batch_size, visibility_timeout ):
			sqs_client = get_aws_client(
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
		def map_sqs_to_lambda( self, credentials, sqs_arn, lambda_arn, batch_size ):
			lambda_client = get_aws_client(
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
		def read_from_s3_and_return_input( self, credentials, s3_bucket, path ):
			return_data = TaskSpawner._read_from_s3(
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
		def read_from_s3( self, credentials, s3_bucket, path ):
			return TaskSpawner._read_from_s3(
				credentials,
				s3_bucket,
				path
			)
		
		@staticmethod
		def _read_from_s3( credentials, s3_bucket, path ):
			s3_client = get_aws_client(
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
		def bulk_s3_delete( self, credentials, s3_bucket, s3_path_list ):
			s3_client = get_aws_client(
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
		def get_s3_pipeline_execution_logs( self, credentials, s3_prefix, max_results ):
			return TaskSpawner.get_all_s3_paths(
				credentials,
				credentials[ "logs_bucket" ],
				s3_prefix,
				max_results
			)
			
		@run_on_executor
		def get_build_packages( self, credentials, s3_prefix, max_results ):
			return TaskSpawner.get_all_s3_paths(
				credentials,
				credentials[ "lambda_packages_bucket" ],
				s3_prefix,
				max_results
			)
		
		@run_on_executor
		def get_s3_list_from_prefix( self, credentials, s3_bucket, s3_prefix, continuation_token, start_after ):
			s3_client = get_aws_client(
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
		def get_all_s3_paths( credentials, s3_bucket, prefix, max_results, **kwargs ):
			s3_client = get_aws_client(
				"s3",
				credentials,
			)
			
			return_array = []
			continuation_token = False
			if max_results == -1: # max_results -1 means get all results
				max_keys = 1000
			elif max_results <= 1000:
				max_keys = max_results
			else:
				max_keys = 1000
			
			# First check to prime it
			response = s3_client.list_objects_v2(
				Bucket=s3_bucket,
				Prefix=prefix,
				MaxKeys=max_keys, # Max keys you can request at once
				**kwargs
			)
			
			while True:
				if continuation_token:
					# Grab another page of results
					response = s3_client.list_objects_v2(
						Bucket=s3_bucket,
						Prefix=prefix,
						MaxKeys=max_keys, # Max keys you can request at once
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
					
				if response[ "IsTruncated" ] == False:
					break
				
				continuation_token = response[ "NextContinuationToken" ]
					
			return return_array
			
		@run_on_executor
		def get_s3_pipeline_execution_ids( self, credentials, timestamp_prefix, max_results, continuation_token ):
			return TaskSpawner.get_all_s3_prefixes(
				credentials,
				credentials[ "logs_bucket" ],
				timestamp_prefix,
				max_results,
				continuation_token
			)
		
		@run_on_executor
		def get_s3_pipeline_timestamp_prefixes( self, credentials, project_id, max_results, continuation_token ):
			return TaskSpawner.get_all_s3_prefixes(
				credentials,
				credentials[ "logs_bucket" ],
				project_id + "/",
				max_results,
				continuation_token
			)

		@staticmethod
		def get_all_s3_prefixes( credentials, s3_bucket, prefix, max_results, continuation_token ):
			s3_client = get_aws_client(
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
			
			while True:
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
					
				if response[ "IsTruncated" ] == False:
					break
					
			return {
				"prefixes": return_array,
				"continuation_token": continuation_token
			}
			
		@run_on_executor
		def get_aws_lambda_existence_info( self, credentials, id, type, lambda_name ):
			return TaskSpawner._get_aws_lambda_existence_info( credentials, id, type, lambda_name )
		
		@staticmethod
		def _get_aws_lambda_existence_info( credentials, id, type, lambda_name ):
			lambda_client = get_aws_client(
				"lambda",
				credentials
			)
			
			try:
				response = lambda_client.get_function(
					FunctionName=lambda_name
				)
			except lambda_client.exceptions.ResourceNotFoundException:
				return {
					"id": id,
					"type": type,
					"name": lambda_name,
					"exists": False
				}
				
			return {
				"id": id,
				"type": type,
				"name": lambda_name,
				"exists": True,
				"arn": response[ "Configuration" ][ "FunctionArn" ]
			}
			
		@run_on_executor
		def get_lambda_cloudwatch_logs( self, credentials, log_group_name, stream_id ):
			return TaskSpawner._get_lambda_cloudwatch_logs( credentials, log_group_name, stream_id )
		
		@staticmethod
		def _get_lambda_cloudwatch_logs( credentials, log_group_name, stream_id ):
			cloudwatch_logs_client = get_aws_client(
				"logs",
				credentials
			)
			
			if stream_id == False:
				# Pull the last stream from CloudWatch
				# Streams take time to propogate so wait if needed
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
		def get_cloudwatch_existence_info( self, credentials, id, type, name ):
			return TaskSpawner._get_cloudwatch_existence_info( credentials, id, type, name )
			
		@staticmethod
		def _get_cloudwatch_existence_info( credentials, id, type, name ):
			events_client = get_aws_client(
				"events",
				credentials
			)
			
			try:
				response = events_client.describe_rule(
					Name=name,
				)
			except events_client.exceptions.ResourceNotFoundException:
				return {
					"id": id,
					"type": type,
					"name": name,
					"exists": False
				}
			
			return {
				"id": id,
				"type": type,
				"name": name,
				"arn": response[ "Arn" ],
				"exists": True,
			}
			
		@run_on_executor
		def get_sqs_existence_info( self, credentials, id, type, name ):
			return TaskSpawner._get_sqs_existence_info( credentials, id, type, name )
			
		@staticmethod
		def _get_sqs_existence_info( credentials, id, type, name ):
			sqs_client = get_aws_client(
				"sqs",
				credentials,
			)
			
			try:
				queue_url_response = sqs_client.get_queue_url(
					QueueName=name,
				)
			except sqs_client.exceptions.QueueDoesNotExist:
				return {
					"id": id,
					"type": type,
					"name": name,
					"exists": False
				}
			
			return {
				"id": id,
				"type": type,
				"name": name,
				"arn": "arn:aws:sqs:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + name,
				"exists": True,
			}
			
		@run_on_executor
		def get_sns_existence_info( self, credentials, id, type, name ):
			return TaskSpawner._get_sns_existence_info( credentials, id, type, name )
			
		@staticmethod
		def _get_sns_existence_info( credentials, id, type, name ):
			sns_client = get_aws_client(
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
					"id": id,
					"type": type,
					"name": name,
					"exists": False
				}
			
			return {
				"id": id,
				"type": type,
				"name": name,
				"arn": sns_topic_arn,
				"exists": True,
			}

		@run_on_executor
		def create_rest_api( self, credentials, name, description, version ):
			api_gateway_client = get_aws_client(
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
		def deploy_api_gateway_to_stage( self, credentials, rest_api_id, stage_name ):
			api_gateway_client = get_aws_client(
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
		def create_resource( self, credentials, rest_api_id, parent_id, path_part ):
			api_gateway_client = get_aws_client(
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
		def create_method( self, credentials, method_name, rest_api_id, resource_id, http_method, api_key_required ):
			api_gateway_client = get_aws_client(
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
		def clean_lambda_iam_policies( self, credentials, lambda_name ):
			lambda_client = get_aws_client(
				"lambda",
				credentials
			)
			
			api_gateway_client = get_aws_client(
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
		def add_integration_response( self, credentials, rest_api_id, resource_id, http_method, lambda_name ):
			api_gateway_client = get_aws_client(
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
		def link_api_method_to_lambda( self, credentials, rest_api_id, resource_id, http_method, api_path, lambda_name ):
			api_gateway_client = get_aws_client(
				"apigateway",
				credentials
			)
			
			lambda_client = get_aws_client(
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


local_tasks = TaskSpawner()


class RunLambda( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Run a Lambda which has been deployed in production.
		"""
		schema = {
			"type": "object",
			"properties": {
				"input_data": {},
				"backpack": {},
				"arn": {
					"type": "string",
				},
				"execution_id": {
					"type": "string",
				},
				"debug_id": {
					"type": "string",
				}
			},
			"required": [
				"input_data",
				"arn"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Running Lambda with ARN of '" + self.json[ "arn" ] + "'..." )
		
		credentials = self.get_authenticated_user_cloud_configuration()
		
		backpack_data = {}
		input_data = self.json[ "input_data" ]

		if "backpack" in self.json:
			# Try to parse backpack as JSON
			try:
				backpack_data = json.loads(
					self.json[ "backpack" ]
				)
			except ValueError:
				self.write({
					"success": False,
					"failure_msg": "Unable to read backpack data JSON",
					"failure_reason": "InvalidBackpackJson"
				})
				return
		
		# Try to parse Lambda input as JSON
		try:
			input_data = json.loads(
				self.json[ "input_data" ]
			)
		except ValueError:
			pass

		lambda_input_data = {
			"_refinery": {
				"backpack": backpack_data,
				"throw_exceptions_fully": True,
				"input_data": input_data
			}
		}

		if "execution_id" in self.json and self.json[ "execution_id" ]:
			lambda_input_data[ "_refinery" ][ "execution_id" ] = str( self.json[ "execution_id" ] )
			
		if "debug_id" in self.json:
			lambda_input_data[ "_refinery" ][ "live_debug" ] = {
				"debug_id": self.json[ "debug_id" ],
				"websocket_uri": LAMBDA_CALLBACK_ENDPOINT,
			}
			
		logit( "Executing Lambda..." )
		lambda_result = yield local_tasks.execute_aws_lambda(
			credentials,
			self.json[ "arn" ],
			lambda_input_data
		)
		
		self.write({
			"success": True,
			"result": lambda_result
		})


def get_base_lambda_code( language, code ):
	if language == "python3.6":
		return TaskSpawner._get_python36_base_code(
			code
		)
	elif language == "python2.7":
		return TaskSpawner._get_python27_base_code(
			code
		)
	elif language == "nodejs8.10":
		return TaskSpawner._get_nodejs_810_base_code(
			code
		)
	elif language == "nodejs10.16.3":
		return TaskSpawner._get_nodejs_10163_base_code(
			code
		)
	elif language == "php7.3":
		return TaskSpawner._get_php_73_base_code(
			code
		)
	elif language == "ruby2.6.4":
		return TaskSpawner._get_ruby_264_base_code(
			code
		)


class RunTmpLambda( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Build, deploy, and run an AWS lambda function.
		
		Always upon completion the Lambda should be deleted!
		"""
		schema = {
			"type": "object",
			"properties": {
				"input_data": {},
				"backpack": {},
				"language": {
					"type": "string",
				},
				"code": {
					"type": "string",
				},
				"libraries": {
					"type": "array",
				},
				"memory": {
					"type": "integer",
				},
				"max_execution_time": {
					"type": "integer",
				},
				"environment_variables": {
					"type": "array"
				},
				"layers": {
					"type": "array"
				},
				"debug_id": {
					"type": "string"
				},
				"shared_files": {
					"type": "array",
					"default": [],
					"items": {
						"type": "object",
						"properties": {
							"body": {
								"type": "string"
							},
							"version": {
								"type": "string"
							},
							"type": {
								"type": "string"
							},
							"id": {
								"type": "string"
							},
							"name": {
								"type": "string"
							}
						},
						"required": [
							"body",
							"version",
							"type",
							"id",
							"name"
						]
					}
				}
			},
			"required": [
				"input_data",
				"language",
				"code",
				"libraries",
				"memory",
				"max_execution_time",
				"environment_variables",
				"layers"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Building Lambda package..." )
		
		credentials = self.get_authenticated_user_cloud_configuration()
		
		random_node_id = get_random_node_id()
		
		# Try to parse Lambda input as JSON
		self.json[ "input_data" ] = attempt_json_decode(
			self.json[ "input_data" ]
		)
		
		backpack_data = {}
		
		if "backpack" in self.json:
			backpack_data = attempt_json_decode(
				self.json[ "backpack" ]
			)
		
		# Empty transitions data
		empty_transitions_dict = {
			"then": [],
			"exception": [],
			"fan-out": [],
			"else": [],
			"fan-in": [],
			"if": [],
			"merge": []
		}
		
		# Dummy pipeline execution ID
		pipeline_execution_id = "SHOULD_NEVER_HAPPEN_TMP_LAMBDA_RUN"

		# Lambda layers to add
		lambda_layers = get_layers_for_lambda( self.json[ "language" ] ) + self.json[ "layers" ]

		# Create Lambda object
		inline_lambda = Lambda(
			name=random_node_id,
			language=self.json[ "language" ],
			code=self.json[ "code" ],
			libraries=self.json[ "libraries" ],
			max_execution_time=self.json[ "max_execution_time" ],
			memory=self.json[ "memory" ],
			transitions=empty_transitions_dict,
			execution_mode="REGULAR",
			execution_pipeline_id=pipeline_execution_id,
			execution_log_level="LOG_NONE",
			environment_variables=self.json[ "environment_variables" ],
			layers=lambda_layers,
			reserved_concurrency_count=False,
			is_inline_execution=True,
			shared_files_list=self.json[ "shared_files" ]
		)

		# Get inline hash key
		environment_variables = get_environment_variables_for_lambda(
			credentials,
			inline_lambda
		)

		inline_lambda_hash_key = TaskSpawner._get_inline_lambda_hash_key(
			self.json[ "language" ],
			self.json[ "max_execution_time" ],
			self.json[ "memory" ],
			environment_variables,
			lambda_layers,
			self.json[ "libraries" ]
		)
		
		cached_inline_execution_lambda = None
		
		if not ( self.json[ "language" ] in NOT_SUPPORTED_INLINE_EXECUTION_LANGUAGES ):
			# Check if we already have an inline execution Lambda for it.
			cached_inline_execution_lambda = self.dbsession.query( InlineExecutionLambda ).filter_by(
				aws_account_id=credentials[ "id" ],
				unique_hash_key=inline_lambda_hash_key
			).first()
		
		# We can skip this if we already have a cached execution
		if cached_inline_execution_lambda:
			logit( "Inline execution is already cached as a Lambda, doing a hotload..." )
			
			# Update the latest execution time to be the current timestamp
			# This informs our garbage collection to ensure we always delete the Lambda
			# that was run the longest ago (so that people encounter cache-misses as
			# little as possible.)
			cached_inline_execution_lambda.last_used_timestamp = int( time.time() )
			
			# Update it in the database
			self.dbsession.commit()
			
			cached_inline_execution_lambda_dict = cached_inline_execution_lambda.to_dict()
			
			lambda_info = {
				"arn": cached_inline_execution_lambda_dict[ "arn" ]
			}
		else:
			try:
				lambda_info = yield deploy_lambda(
					credentials,
					random_node_id,
					inline_lambda
				)
			except BuildException as build_exception:
				self.write({
					"success": False,
					"msg": "An error occurred while building the Code Block package.",
					"log_output": build_exception.build_output
				})
				raise gen.Return()
			except botocore.exceptions.ClientError as boto_error:
				logit( "An exception occurred while setting up the Code Block." )
				logit( boto_error )

				error_message = boto_error.response[ "Error" ][ "Message" ] + " (Code: " + boto_error.response[ "Error" ][ "Code" ] + ")"

				self.write({
					"success": False,
					"msg": error_message,
					"log_output": ""
				})
				raise gen.Return()
				
		execute_lambda_params = {
			"_refinery": {
				"backpack": backpack_data,
				"throw_exceptions_fully": True,
				"input_data": self.json[ "input_data" ],
				"temporary_execution": True
			}
		}

		# Get inline execution code
		inline_execution_code = get_base_lambda_code(
			self.json[ "language" ],
			self.json[ "code" ]
		)

		# Generate Lambda run input
		execute_lambda_params[ "_refinery" ][ "inline_code" ] = {
			"base_code": inline_execution_code,
			"shared_files": self.json[ "shared_files" ]
		}
		
		if "debug_id" in self.json:
			execute_lambda_params[ "_refinery" ][ "live_debug" ] = {
				"debug_id": self.json[ "debug_id" ],
				"websocket_uri": LAMBDA_CALLBACK_ENDPOINT,
			}
		
		logit( "Executing Lambda '" + lambda_info[ "arn" ] + "'..." )
		
		lambda_result = yield local_tasks.execute_aws_lambda(
			credentials,
			lambda_info[ "arn" ],
			execute_lambda_params
		)

		if "Task timed out after " in lambda_result[ "logs" ]:
			logit( "Lambda timed out while being executed!" )
			self.write({
				"success": False,
				"msg": "The Code Block timed out while running, you may have an infinite loop or you may need to increase your Code Block's Max Execution Time.",
				"log_output": ""
			})
			raise gen.Return()
		
		try:
			return_data = json.loads(
				lambda_result[ "returned_data" ]
			)
			s3_object = yield local_tasks.read_from_s3(
				credentials,
				credentials[ "logs_bucket" ],
				return_data[ "_refinery" ][ "indirect" ][ "s3_path" ]
			)
			s3_dict = json.loads(
				s3_object
			)
			lambda_result[ "returned_data" ] = json.dumps(
				s3_dict[ "return_data" ],
				indent=4,
			)
			lambda_result[ "logs" ] = s3_dict[ "program_output" ]
		except Exception, e:
			logit( "Exception occurred while loading temporary Lambda return data: " )
			logit( e )
			logit( "Raw Lambda return data: " )
			logit( lambda_result )

			# Clearer logging for raw Lambda error output
			if "logs" in lambda_result:
				print( lambda_result[ "logs" ] )

			self.write({
				"success": False,
				"msg": "An exception occurred while running the Lambda.",
				"log_output": str( e )
			})
			raise gen.Return()
		
		# If it's not a supported language for inline execution that
		# means that it needs to be manually deleted since it's not in the
		# regular garbage collection pool.
		if self.json[ "language" ] in NOT_SUPPORTED_INLINE_EXECUTION_LANGUAGES:
			logit( "Deleting Lambda..." )
			
			# Now we delete the lambda, don't yield because we don't need to wait
			delete_result = local_tasks.delete_aws_lambda(
				credentials,
				random_node_id
			)

		self.write({
			"success": True,
			"result": lambda_result
		})
		
def get_lambda_safe_name( input_name ):
	whitelist = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
	input_name = input_name.replace( " ", "_" )
	return "".join([c for c in input_name if c in whitelist])[:64]
	
def get_language_specific_environment_variables( language ):
	environment_variables_list = []
	
	if language == "python2.7" or language == "python3.6":
		environment_variables_list.append({
			"key": "PYTHONPATH",
			"value": "/var/task/",
		})
		environment_variables_list.append({
			"key": "PYTHONUNBUFFERED",
			"value": "1",
		})
	elif language == "nodejs8.10" or language == "nodejs10.16.3":
		environment_variables_list.append({
			"key": "NODE_PATH",
			"value": "/var/task/node_modules/",
		})
		
	return environment_variables_list

def get_environment_variables_for_lambda( credentials, lambda_object ):
	all_environment_vars = copy.copy( lambda_object.environment_variables )
	
	# Add environment variables depending on language
	# This is mainly for module loading when we're doing inline executions.
	all_environment_vars = all_environment_vars + get_language_specific_environment_variables(
		lambda_object.language
	)
	
	all_environment_vars.append({
		"key": "REDIS_HOSTNAME",
		"value": credentials[ "redis_hostname" ],
	})
	
	all_environment_vars.append({
		"key": "REDIS_PASSWORD",
		"value": credentials[ "redis_password" ],
	})

	all_environment_vars.append({
		"key": "REDIS_PORT",
		"value": str( credentials[ "redis_port" ] ),
	})

	all_environment_vars.append({
		"key": "EXECUTION_PIPELINE_ID",
		"value": lambda_object.execution_pipeline_id,
	})
	
	all_environment_vars.append({
		"key": "LOG_BUCKET_NAME",
		"value": credentials[ "logs_bucket" ],
	})

	all_environment_vars.append({
		"key": "PIPELINE_LOGGING_LEVEL",
		"value": lambda_object.execution_log_level,
	})
	
	all_environment_vars.append({
		"key": "EXECUTION_MODE",
		"value": lambda_object.execution_mode,
	})
	
	all_environment_vars.append({
		"key": "TRANSITION_DATA",
		"value": json.dumps(
			lambda_object.transitions
		),
	})
	
	if lambda_object.is_inline_execution and not lambda_object.language in NOT_SUPPORTED_INLINE_EXECUTION_LANGUAGES:
		# The environment variable activates it as
		# an inline execution Lambda and allows us to
		# pass in arbitrary code to execution.
		all_environment_vars.append({
			"key": "IS_INLINE_EXECUTOR",
			"value": "True",
		})
		
	return all_environment_vars
	
def get_layers_for_lambda( language ):
	"""
	IGNORE THIS NOTICE AT YOUR OWN PERIL. YOU HAVE BEEN WARNED.
	
	All layers are managed under our root AWS account at 134071937287.
	
	When a new layer is published the ARNs must be updated in source intentionally
	so that whoever does so must read this notice and understand what MUST
	be done before updating the Refinery customer runtime for customers.
	
	You must do the following:
	* Extensively test the new custom runtime.
	* Upload the new layer version to the root AWS account.
	* Run the following command on the root account to publically allow use of the layer:
	
	aws lambda add-layer-version-permission \
	--layer-name REPLACE_ME_WITH_LAYER_NAME \
	--version-number REPLACE_ME_WITH_LAYER_VERSION \
	--statement-id public \
	--action lambda:GetLayerVersion \
	--principal "*" \
	--region us-west-2
	
	* Test the layer in a development version of Refinery to ensure it works.
	* Update the source code with the new layer ARN
	
	Once this is done all future deployments will use the new layers.
	"""
	new_layers = []
	
	# Add the custom runtime layer in all cases
	if language == "nodejs8.10":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-node810-custom-runtime:30"
		)
	elif language == "nodejs10.16.3":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-nodejs10-custom-runtime:9"
		)
	elif language == "php7.3":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-php73-custom-runtime:28"
		)
	elif language == "go1.12":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-go112-custom-runtime:28"
		)
	elif language == "python2.7":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-python27-custom-runtime:28"
		)
	elif language == "python3.6":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-python36-custom-runtime:29"
		)
	elif language == "ruby2.6.4":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-ruby264-custom-runtime:29"
		)
		
	return new_layers

@gen.coroutine
def deploy_lambda( credentials, id, lambda_object ):
	"""
	Here we build the default required environment variables.
	"""
	lambda_object.environment_variables = get_environment_variables_for_lambda(
		credentials,
		lambda_object
	)

	logit(
		"Deploying '" + lambda_object.name + "' Lambda package to production..."
	)
	
	lambda_object.role = "arn:aws:iam::" + str( credentials[ "account_id" ] ) + ":role/refinery_default_aws_lambda_role"
	
	# If it's a self-hosted (THIRDPARTY) AWS account we deploy with a different role
	# name which they manage themselves.
	if credentials[ "account_type" ] == "THIRDPARTY":
		lambda_object.role = "arn:aws:iam::" + str( credentials[ "account_id" ] ) + ":role/" + THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
		
	# Don't yield for it, but we'll also create a log group at the same time
	# We're set a tag for that log group for cost tracking
	local_tasks.create_cloudwatch_group(
		credentials,
		"/aws/lambda/" + lambda_object.name,
		{
			"RefineryResource": "true"
		},
		7
	)

	deployed_lambda_data = yield local_tasks.deploy_aws_lambda(
		credentials,
		lambda_object
	)
	
	# If we have concurrency set, then we'll set that for our deployed Lambda
	if lambda_object.reserved_concurrency_count:
		logit( "Setting reserved concurrency for Lambda '" + deployed_lambda_data[ "FunctionArn" ] + "' to " + str( lambda_object.reserved_concurrency_count ) + "..." )
		yield local_tasks.set_lambda_reserved_concurrency(
			credentials,
			deployed_lambda_data[ "FunctionArn" ],
			lambda_object.reserved_concurrency_count
		)
	
	raise gen.Return({
		"id": id,
		"name": lambda_object.name,
		"arn": deployed_lambda_data[ "FunctionArn" ]
	})
	
def get_node_by_id( target_id, workflow_states ):
	for workflow_state in workflow_states:
		if workflow_state[ "id" ] == target_id:
			return workflow_state
	
	return False
	
def update_workflow_states_list( updated_node, workflow_states ):
	for i in range( 0, len( workflow_states ) ):
		if workflow_states[i][ "id" ] == updated_node[ "id" ]:
			workflow_states[i] = updated_node
			break
		
	return workflow_states

def get_merge_lambda_arn_list( target_id, workflow_relationships, workflow_states ):
	# First we create a list of Node IDs
	id_target_list = []

	for workflow_relationship in workflow_relationships:
		if workflow_relationship[ "type" ] != "merge":
			continue

		if workflow_relationship[ "next" ] != target_id:
			continue

		id_target_list.append(
			workflow_relationship[ "node" ]
		)

	arn_list = []

	for workflow_state in workflow_states:
		if workflow_state[ "id" ] in id_target_list:
			arn_list.append(
				workflow_state[ "arn" ]
			)

	return arn_list
	
@gen.coroutine
def deploy_diagram( credentials, project_name, project_id, diagram_data, project_config ):
	"""
	Deploy the diagram to AWS
	"""
	
	"""
	Process workflow relationships and tag Lambda
	nodes with an array of transitions.
	"""

	# Kick off the creation of the log table for the project ID
	# This is fine to do if one already exists because the SQL
	# query explicitly specifies not to create one if it exists.
	project_log_table_future = local_tasks.create_project_id_log_table(
		credentials,
		project_id
	)

	# Random ID to keep deploy ARNs unique
	# TODO do more research into collision probability
	unique_deploy_id = get_random_deploy_id()
	
	unique_name_counter = 0
	
	# Environment variable map
	# { "LAMBDA_UUID": [{ "key": "", "value": ""}] }
	env_var_dict = {}
	
	# First just set an empty array for each lambda node
	for workflow_state in diagram_data[ "workflow_states" ]:
		# Update all of the workflow states with new random deploy ID
		if "name" in workflow_state:
			workflow_state[ "name" ] += unique_deploy_id + str(unique_name_counter)
			
		# Make an environment variable array if there isn't one already
		env_var_dict[ workflow_state[ "id" ] ] = []
		
		# If there are environment variables in project_config, add them to the Lambda node data
		if workflow_state[ "type" ] == "lambda" and "environment_variables" in workflow_state:
			for env_var_uuid, env_data in workflow_state[ "environment_variables" ].iteritems():
				if env_var_uuid in project_config[ "environment_variables" ]:
					# Add value to match schema
					workflow_state[ "environment_variables" ][ env_var_uuid ][ "value" ] = project_config[ "environment_variables" ][ env_var_uuid ][ "value" ]
					env_var_dict[ workflow_state[ "id" ] ].append({
						"key": workflow_state[ "environment_variables" ][ env_var_uuid ][ "name" ],
						"value": project_config[ "environment_variables" ][ env_var_uuid ][ "value" ]
					})
		
		if workflow_state[ "type" ] == "lambda" or workflow_state[ "type" ] == "api_endpoint":
			# Set up default transitions data
			workflow_state[ "transitions" ] = {}
			workflow_state[ "transitions" ][ "if" ] = []
			workflow_state[ "transitions" ][ "else" ] = []
			workflow_state[ "transitions" ][ "exception" ] = []
			workflow_state[ "transitions" ][ "then" ] = []
			workflow_state[ "transitions" ][ "fan-out" ] = []
			workflow_state[ "transitions" ][ "fan-in" ] = []
			workflow_state[ "transitions" ][ "merge" ] = []
			
		unique_name_counter = unique_name_counter + 1
		
	"""
	Here we calculate the teardown data ahead of time.
	
	This is used when we encounter an error during the
	deployment process which requires us to roll back.
	When the rollback occurs we pass our previously-generated
	list and pass it to the tear down function.
	
	[
		{
			"id": {{node_id}},
			"arn": {{production_resource_arn}},
			"name": {{node_name}},
			"type": {{node_type}},
		}
	]
	"""
	teardown_nodes_list = []
	
	
	"""
	This holds all of the exception data which occurred during a
	deployment. Upon an unhandled exception occurring we rollback
	and teardown what's been deployed so far. After that we return
	an error to the user with information on what caused the deploy
	to fail.
	
	[
		{
			"type": "", # The type of the deployed node
			"name": "", # The name of the specific node
			"id": "", # The ID of the specific node
			"exception": "", # String of the exception details
		}
	]
	"""
	deployment_exceptions = []

	for workflow_state in diagram_data[ "workflow_states" ]:
		if workflow_state[ "type" ] == "lambda":
			node_arn = "arn:aws:lambda:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":function:" + get_lambda_safe_name( workflow_state[ "name" ] )
		elif workflow_state[ "type" ] == "sns_topic":
			node_arn = "arn:aws:sns:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + get_lambda_safe_name( workflow_state[ "name" ] )
		elif workflow_state[ "type" ] == "sqs_queue":
			node_arn = "arn:aws:sqs:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + get_lambda_safe_name( workflow_state[ "name" ] )
		elif workflow_state[ "type" ] == "schedule_trigger":
			node_arn = "arn:aws:events:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":rule/" + get_lambda_safe_name( workflow_state[ "name" ] )
		elif workflow_state[ "type" ] == "api_endpoint":
			node_arn = "arn:aws:lambda:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":function:" + get_lambda_safe_name( workflow_state[ "name" ] )
		else:
			node_arn = False
		
		# For pseudo-nodes like API Responses we don't need to create a teardown entry
		if node_arn:
			# Set ARN on workflow state
			workflow_state[ "arn" ] = node_arn

			teardown_nodes_list.append({
				"id": workflow_state[ "id" ],
				"arn": node_arn,
				"name": get_lambda_safe_name( workflow_state[ "name" ] ),
				"type": workflow_state[ "type" ],
			})
		
	# Now add transition data to each Lambda
	for workflow_relationship in diagram_data[ "workflow_relationships" ]:
		origin_node_data = get_node_by_id(
			workflow_relationship[ "node" ],
			diagram_data[ "workflow_states" ]
		)
		
		target_node_data = get_node_by_id(
			workflow_relationship[ "next" ],
			diagram_data[ "workflow_states" ]
		)
		
		if origin_node_data[ "type" ] == "lambda" or origin_node_data[ "type" ] == "api_endpoint":
			if target_node_data[ "type" ] == "lambda":
				target_arn = "arn:aws:lambda:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":function:" + get_lambda_safe_name( target_node_data[ "name" ] )
			elif target_node_data[ "type" ] == "sns_topic":
				target_arn = "arn:aws:sns:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] )+ ":" + get_lambda_safe_name( target_node_data[ "name" ] )
			elif target_node_data[ "type" ] == "api_gateway_response":
				# API Gateway responses are a pseudo node and don't have an ARN
				target_arn = False
			elif target_node_data[ "type" ] == "sqs_queue":
				target_arn = "arn:aws:sqs:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + get_lambda_safe_name( target_node_data[ "name" ] )
			
			if workflow_relationship[ "type" ] == "then":
				origin_node_data[ "transitions" ][ "then" ].append({
					"type": target_node_data[ "type" ],
					"arn": target_arn,
				})
			elif workflow_relationship[ "type" ] == "else":
				origin_node_data[ "transitions" ][ "else" ].append({
					"type": target_node_data[ "type" ],
					"arn": target_arn,
				})
			elif workflow_relationship[ "type" ] == "exception":
				origin_node_data[ "transitions" ][ "exception" ].append({
					"type": target_node_data[ "type" ],
					"arn": target_arn,
				})
			elif workflow_relationship[ "type" ] == "if":
				origin_node_data[ "transitions" ][ "if" ].append({
					"arn": target_arn,
					"type": target_node_data[ "type" ],
					"expression": workflow_relationship[ "expression" ]
				})
			elif workflow_relationship[ "type" ] == "fan-out":
				origin_node_data[ "transitions" ][ "fan-out" ].append({
					"type": target_node_data[ "type" ],
					"arn": target_arn,
				})
			elif workflow_relationship[ "type" ] == "fan-in":
				origin_node_data[ "transitions" ][ "fan-in" ].append({
					"type": target_node_data[ "type" ],
					"arn": target_arn,
				})
			elif workflow_relationship[ "type" ] == "merge":
				origin_node_data[ "transitions" ][ "merge" ].append({
					"type": target_node_data[ "type" ],
					"arn": target_arn,
					"merge_lambdas": get_merge_lambda_arn_list(
						target_node_data[ "id" ],
						diagram_data[ "workflow_relationships" ],
						diagram_data[ "workflow_states" ]
					)
				})
				
			diagram_data[ "workflow_states" ] = update_workflow_states_list(
				origin_node_data,
				diagram_data[ "workflow_states" ]
			)
	
	"""
	Separate out nodes into different types
	"""
	lambda_nodes = []
	schedule_trigger_nodes = []
	sqs_queue_nodes = []
	sns_topic_nodes = []
	api_endpoint_nodes = []
	
	for workflow_state in diagram_data[ "workflow_states" ]:
		if workflow_state[ "type" ] == "lambda":
			lambda_nodes.append(
				workflow_state
			)
		elif workflow_state[ "type" ] == "schedule_trigger":
			schedule_trigger_nodes.append(
				workflow_state
			)
		elif workflow_state[ "type" ] == "sqs_queue":
			sqs_queue_nodes.append(
				workflow_state
			)
		elif workflow_state[ "type" ] == "sns_topic":
			sns_topic_nodes.append(
				workflow_state
			)
		elif workflow_state[ "type" ] == "api_endpoint":
			api_endpoint_nodes.append(
				workflow_state
			)
	
	"""
	Deploy all Lambdas to production
	"""
	lambda_node_deploy_futures = []
	
	for lambda_node in lambda_nodes:
		lambda_safe_name = get_lambda_safe_name( lambda_node[ "name" ] )
		logit( "Deploying Lambda '" + lambda_safe_name + "'..." )

		# For backwards compatibility
		if not ( "reserved_concurrency_count" in lambda_node ):
			lambda_node[ "reserved_concurrency_count" ] = False

		lambda_layers = get_layers_for_lambda(
			lambda_node[ "language" ]
		) + lambda_node[ "layers" ]

		shared_files = get_shared_files_for_lambda(
			lambda_node[ "id" ],
			diagram_data
		)

		# Create Lambda object
		lambda_object = Lambda(
			name=lambda_safe_name,
			language=lambda_node[ "language" ],
			code=lambda_node[ "code" ],
			libraries=lambda_node[ "libraries" ],
			max_execution_time=lambda_node[ "max_execution_time" ],
			memory=lambda_node[ "memory" ],
			transitions=lambda_node[ "transitions" ],
			execution_mode="REGULAR",
			execution_pipeline_id=project_id,
			execution_log_level=project_config[ "logging" ][ "level" ],
			environment_variables=env_var_dict[ lambda_node[ "id" ] ],
			layers=lambda_layers,
			reserved_concurrency_count=lambda_node[ "reserved_concurrency_count" ],
			is_inline_execution=False,
			shared_files_list=shared_files
		)

		lambda_node_deploy_futures.append({
			"id": lambda_node[ "id" ],
			"name": lambda_safe_name,
			"type": lambda_node[ "type" ],
			"future": deploy_lambda(
				credentials,
				lambda_node[ "id" ],
				lambda_object
			)
		})
		
	"""
	Deploy all API Endpoints to production
	"""
	api_endpoint_node_deploy_futures = []
	
	for api_endpoint_node in api_endpoint_nodes:
		api_endpoint_safe_name = get_lambda_safe_name( api_endpoint_node[ "name" ] )
		logit( "Deploying API Endpoint '" + api_endpoint_safe_name + "'..." )
		
		lambda_layers = get_layers_for_lambda( "python2.7" )

		# Create Lambda object
		lambda_object = Lambda(
			name=api_endpoint_safe_name,
			language="python2.7",
			code="",
			libraries=[],
			max_execution_time=30,
			memory=512,
			transitions=api_endpoint_node[ "transitions" ],
			execution_mode="API_ENDPOINT",
			execution_pipeline_id=project_id,
			execution_log_level=project_config[ "logging" ][ "level" ],
			environment_variables=[],
			layers=lambda_layers,
			reserved_concurrency_count=False,
			is_inline_execution=False,
			shared_files_list=[]
		)
		
		api_endpoint_node_deploy_futures.append({
			"id": api_endpoint_node[ "id" ],
			"name": get_lambda_safe_name( api_endpoint_node[ "name" ] ),
			"type": api_endpoint_node[ "type" ],
			"future": deploy_lambda(
				credentials,
				api_endpoint_node[ "id" ],
				lambda_object
			)
		})
		
	"""
	Deploy all time triggers to production
	"""
	schedule_trigger_node_deploy_futures = []
	
	for schedule_trigger_node in schedule_trigger_nodes:
		schedule_trigger_name = get_lambda_safe_name( schedule_trigger_node[ "name" ] )
		logit( "Deploying schedule trigger '" + schedule_trigger_name + "'..." )
		schedule_trigger_node_deploy_futures.append({
			"id": schedule_trigger_node[ "id" ],
			"name": schedule_trigger_name,
			"type": schedule_trigger_node[ "type" ],
			"future": local_tasks.create_cloudwatch_rule(
				credentials,
				schedule_trigger_node[ "id" ],
				schedule_trigger_name,
				schedule_trigger_node[ "schedule_expression" ],
				schedule_trigger_node[ "description" ],
				schedule_trigger_node[ "input_string" ],
			)
		})
		
	"""
	Deploy all SQS queues to production
	"""
	sqs_queue_nodes_deploy_futures = []
	
	for sqs_queue_node in sqs_queue_nodes:
		sqs_queue_name = get_lambda_safe_name( sqs_queue_node[ "name" ] )
		logit( "Deploying SQS queue '" + sqs_queue_name + "'..." )
		sqs_queue_nodes_deploy_futures.append({
			"id": sqs_queue_node[ "id" ],
			"name": sqs_queue_name,
			"type": sqs_queue_node[ "type" ],
			"future": local_tasks.create_sqs_queue(
				credentials,
				sqs_queue_node[ "id" ],
				sqs_queue_name,
				int( sqs_queue_node[ "batch_size" ] ), # Not used, passed along
				900, # Max Lambda runtime - TODO set this to the linked Lambda amount
			)
		})
		
	"""
	Deploy all SNS topics to production
	"""
	sns_topic_nodes_deploy_futures = []
	
	for sns_topic_node in sns_topic_nodes:
		sns_topic_name = get_lambda_safe_name( sns_topic_node[ "name" ] )
		logit( "Deploying SNS topic '" + sns_topic_name + "'..." )
		
		sns_topic_nodes_deploy_futures.append({
			"id": sns_topic_node[ "id" ],
			"name": sns_topic_name,
			"type": sns_topic_node[ "type" ],
			"future": local_tasks.create_sns_topic(
				credentials,
				sns_topic_node[ "id" ],
				sns_topic_name,
			)
		})
		
	# Combine futures
	combined_futures_list = []
	combined_futures_list += schedule_trigger_node_deploy_futures
	combined_futures_list += lambda_node_deploy_futures
	combined_futures_list += sqs_queue_nodes_deploy_futures
	combined_futures_list += sns_topic_nodes_deploy_futures
	combined_futures_list += api_endpoint_node_deploy_futures
	
	# Initialize list of results
	deployed_schedule_triggers = []
	deployed_lambdas = []
	deployed_sqs_queues = []
	deployed_sns_topics = []
	deployed_api_endpoints = []
	
	# Wait till everything is deployed
	for deploy_future_data in combined_futures_list:
		try:
			output = yield deploy_future_data[ "future" ]
			
			logit( "Deployed node '" + deploy_future_data[ "name" ] + "' successfully!" )
			
			# Append to approriate lists
			if deploy_future_data[ "type" ] == "lambda":
				deployed_lambdas.append(
					output
				)
			elif deploy_future_data[ "type" ] == "sqs_queue":
				deployed_sqs_queues.append(
					output
				)
			elif deploy_future_data[ "type" ] == "schedule_trigger":
				deployed_schedule_triggers.append(
					output
				)
			elif deploy_future_data[ "type" ] == "sns_topic":
				deployed_sns_topics.append(
					output
				)
			elif deploy_future_data[ "type" ] == "api_endpoint":
				deployed_api_endpoints.append(
					output
				)
		except Exception, e:
			logit( "Failed to deploy node '" + deploy_future_data[ "name" ] + "'!", "error" )
			logit( "The full exception details can be seen below: ", "error" )
			logit( traceback.format_exc(), "error" )
			deployment_exceptions.append({
				"id": deploy_future_data[ "id" ],
				"name": deploy_future_data[ "name" ],
				"type": deploy_future_data[ "type" ],
				"exception": traceback.format_exc()
			})
	
	# This is the earliest point we can apply the breaks in the case of an exception
	# It's the callers responsibility to tear down the nodes
	if len( deployment_exceptions ) > 0:
		logit( "[ ERROR ] An uncaught exception occurred during the deployment process!", "error" )
		logit( deployment_exceptions, "error" )
		raise gen.Return({
			"success": False,
			"teardown_nodes_list": teardown_nodes_list,
			"exceptions": deployment_exceptions,
		})
	
	"""
	Set up API Gateways to be attached to API Endpoints
	"""
	
	# The API Gateway ID
	api_gateway_id = False
	
	# Pull previous API Gateway ID if it exists
	if project_config[ "api_gateway" ][ "gateway_id" ]:
		api_gateway_id = project_config[ "api_gateway" ][ "gateway_id" ]
		logit( "Previous API Gateway exists with ID of '" + api_gateway_id + "'..." )
		
	if len( deployed_api_endpoints ) > 0:
		api_route_futures = []
		
		# Verify the existance of API Gateway before proceeding
		# It could have been deleted.
		logit( "Verifying existance of API Gateway..." )
		if api_gateway_id:
			api_gateway_exists = yield api_gateway_manager.api_gateway_exists(
				credentials,
				api_gateway_id
			)
		else:
			api_gateway_exists = False
		
		# If it doesn't exist we'll set the API Gateway ID to False
		# So that it will be freshly created.
		if not api_gateway_exists:
			api_gateway_id = False
		
		# We need to create an API gateway
		logit( "Deploying API Gateway for API Endpoint(s)..." )
		
		# Create a new API Gateway if one does not already exist
		if api_gateway_id == False:
			# We just generate a random ID for the API Gateway, no great other way to do it.
			# e.g. when you change the project name now it's hard to know what the API Gateway
			# is...
			rest_api_name = "Refinery-API-Gateway_" + str( uuid.uuid4() ).replace(
				"-",
				""
			)
			create_gateway_result = yield local_tasks.create_rest_api(
				credentials,
				rest_api_name,
				"API Gateway created by Refinery. Associated with project ID " + project_id,
				"1.0.0"
			)
			
			api_gateway_id = create_gateway_result[ "id" ]
			
			# Update project config
			project_config[ "api_gateway" ][ "gateway_id" ] = api_gateway_id
		else:
			# We do another strip of the gateway just to be sure
			yield strip_api_gateway(
				credentials,
				project_config[ "api_gateway" ][ "gateway_id" ],
			)
		
		# Add the API Gateway as a new node
		diagram_data[ "workflow_states" ].append({
			"id": get_random_node_id(),
			"type": "api_gateway",
			"name": "__api_gateway__",
			"rest_api_id": api_gateway_id,
		})
		
		for deployed_api_endpoint in deployed_api_endpoints:
			for workflow_state in diagram_data[ "workflow_states" ]:
				if workflow_state[ "id" ] == deployed_api_endpoint[ "id" ]:
					logit( "Setting up route " + workflow_state[ "http_method" ] + " " + workflow_state[ "api_path" ] + " for API Endpoint '" + workflow_state[ "name" ] + "'..." )
					yield create_lambda_api_route(
						credentials,
						api_gateway_id,
						workflow_state[ "http_method" ],
						workflow_state[ "api_path" ],
						deployed_api_endpoint[ "name" ],
						True
					)
					
					
		logit( "Now deploying API gateway to stage..." )
		deploy_stage_results = yield local_tasks.deploy_api_gateway_to_stage(
			credentials,
			api_gateway_id,
			"refinery"
		)

	"""
	Update all nodes with deployed ARN for easier teardown
	"""
	# Update workflow lambda nodes with arn
	for deployed_lambda in deployed_lambdas:
		for workflow_state in diagram_data[ "workflow_states" ]:
			if workflow_state[ "id" ] == deployed_lambda[ "id" ]:
				workflow_state[ "arn" ] = deployed_lambda[ "arn" ]
				workflow_state[ "name" ] = deployed_lambda[ "name" ]
				
	# Update workflow API Endpoint nodes with arn
	for deployed_api_endpoint in deployed_api_endpoints:
		for workflow_state in diagram_data[ "workflow_states" ]:
			if workflow_state[ "id" ] == deployed_api_endpoint[ "id" ]:
				workflow_state[ "arn" ] = deployed_api_endpoint[ "arn" ]
				workflow_state[ "name" ] = deployed_api_endpoint[ "name" ]
				workflow_state[ "rest_api_id" ] = api_gateway_id
				workflow_state[ "url" ] = "https://" + api_gateway_id + ".execute-api." + credentials[ "region" ] + ".amazonaws.com/refinery" + workflow_state[ "api_path" ]
				
	# Update workflow scheduled trigger nodes with arn
	for deployed_schedule_trigger in deployed_schedule_triggers:
		for workflow_state in diagram_data[ "workflow_states" ]:
			if workflow_state[ "id" ] == deployed_schedule_trigger[ "id" ]:
				workflow_state[ "arn" ] = deployed_schedule_trigger[ "arn" ]
				workflow_state[ "name" ] = deployed_schedule_trigger[ "name" ]
				
	# Update SQS queue nodes with arn
	for deployed_sqs_queue in deployed_sqs_queues:
		for workflow_state in diagram_data[ "workflow_states" ]:
			if workflow_state[ "id" ] == deployed_sqs_queue[ "id" ]:
				workflow_state[ "arn" ] = deployed_sqs_queue[ "arn" ]
				workflow_state[ "name" ] = deployed_sqs_queue[ "name" ]
				
	# Update SNS topics with arn
	for deployed_sns_topic in deployed_sns_topics:
		for workflow_state in diagram_data[ "workflow_states" ]:
			if workflow_state[ "id" ] == deployed_sns_topic[ "id" ]:
				workflow_state[ "arn" ] = deployed_sns_topic[ "arn" ]
				workflow_state[ "name" ] = deployed_sns_topic[ "name" ]
	
	
	"""
	Link deployed schedule triggers to Lambdas
	"""
	schedule_trigger_pairs_to_deploy = []
	for deployed_schedule_trigger in deployed_schedule_triggers:
		for workflow_relationship in diagram_data[ "workflow_relationships" ]:
			if deployed_schedule_trigger[ "id" ] == workflow_relationship[ "node" ]:
				# Find target node
				for deployed_lambda in deployed_lambdas:
					if deployed_lambda[ "id" ] == workflow_relationship[ "next" ]:
						schedule_trigger_pairs_to_deploy.append({
							"scheduled_trigger": deployed_schedule_trigger,
							"target_lambda": deployed_lambda,
						})
						
	schedule_trigger_targeting_futures = []
	for schedule_trigger_pair in schedule_trigger_pairs_to_deploy:
		schedule_trigger_targeting_futures.append(
			local_tasks.add_rule_target(
				credentials,
				schedule_trigger_pair[ "scheduled_trigger" ][ "name" ],
				schedule_trigger_pair[ "target_lambda" ][ "name" ],
				schedule_trigger_pair[ "target_lambda" ][ "arn" ],
				schedule_trigger_pair[ "scheduled_trigger" ][ "input_string" ]
			)
		)
		
	"""
	Link deployed SQS queues to their target Lambdas
	"""
	sqs_queue_triggers_to_deploy = []
	for deployed_sqs_queue in deployed_sqs_queues:
		for workflow_relationship in diagram_data[ "workflow_relationships" ]:
			if deployed_sqs_queue[ "id" ] == workflow_relationship[ "node" ]:
				# Find target node
				for deployed_lambda in deployed_lambdas:
					if deployed_lambda[ "id" ] == workflow_relationship[ "next" ]:
						sqs_queue_triggers_to_deploy.append({
							"sqs_queue_trigger": deployed_sqs_queue,
							"target_lambda": deployed_lambda,
						})
	
	sqs_queue_trigger_targeting_futures = []
	for sqs_queue_trigger in sqs_queue_triggers_to_deploy:
		sqs_queue_trigger_targeting_futures.append(
			local_tasks.map_sqs_to_lambda(
				credentials,
				sqs_queue_trigger[ "sqs_queue_trigger" ][ "arn" ],
				sqs_queue_trigger[ "target_lambda" ][ "arn" ],
				int( sqs_queue_trigger[ "sqs_queue_trigger" ][ "batch_size" ] )
			)
		)
	
	"""
	Link deployed SNS topics to their Lambdas
	"""
	sns_topic_triggers_to_deploy = []
	for deployed_sns_topic in deployed_sns_topics:
		for workflow_relationship in diagram_data[ "workflow_relationships" ]:
			if deployed_sns_topic[ "id" ] == workflow_relationship[ "node" ]:
				# Find target node
				for deployed_lambda in deployed_lambdas:
					if deployed_lambda[ "id" ] == workflow_relationship[ "next" ]:
						sns_topic_triggers_to_deploy.append({
							"sns_topic_trigger": deployed_sns_topic,
							"target_lambda": deployed_lambda,
						})
	
	sns_topic_trigger_targeting_futures = []
	for sns_topic_trigger in sns_topic_triggers_to_deploy:
		sns_topic_trigger_targeting_futures.append(
			local_tasks.subscribe_lambda_to_sns_topic(
				credentials,
				sns_topic_trigger[ "sns_topic_trigger" ][ "arn" ],
				sns_topic_trigger[ "target_lambda" ][ "arn" ],
			)
		)
	
	# Combine API endpoints and deployed Lambdas since both are
	# Lambdas at the core and need to be warmed.
	combined_warmup_list = []
	combined_warmup_list = combined_warmup_list + json.loads(
		json.dumps(
			deployed_lambdas
		)
	)
	combined_warmup_list = combined_warmup_list + json.loads(
		json.dumps(
			deployed_api_endpoints
		)
	)
	
	if "warmup_concurrency_level" in project_config and project_config[ "warmup_concurrency_level" ]:
		logit( "Adding auto-warming to the deployment..." )
		warmup_concurrency_level = int( project_config[ "warmup_concurrency_level" ] )
		yield add_auto_warmup(
			credentials,
			warmup_concurrency_level,
			unique_deploy_id,
			combined_warmup_list,
			diagram_data
		)
	
	# Wait till are triggers are set up
	deployed_schedule_trigger_targets = yield schedule_trigger_targeting_futures
	sqs_queue_trigger_targets = yield sqs_queue_trigger_targeting_futures
	sns_topic_trigger_targets = yield sns_topic_trigger_targeting_futures
	
	# Make sure that log table is set up
	# It almost certainly is by this point
	yield project_log_table_future

	raise gen.Return({
		"success": True,
		"project_name": project_name,
		"project_id": project_id,
		"deployment_diagram": diagram_data,
		"project_config": project_config
	})

@gen.coroutine
def create_warmer_for_lambda_set( credentials, warmup_concurrency_level, unique_deploy_id, combined_warmup_list, diagram_data ):
	# Create Lambda warmers if enabled
	warmer_trigger_name = "WarmerTrigger" + unique_deploy_id
	logit( "Deploying auto-warmer CloudWatch rule..." )
	warmer_trigger_result = yield local_tasks.create_cloudwatch_rule(
		credentials,
		get_random_node_id(),
		warmer_trigger_name,
		"rate(5 minutes)",
		"A CloudWatch Event trigger to keep the deployed Lambdas warm.",
		"",
	)
	
	diagram_data[ "workflow_states" ].append({
		"id": warmer_trigger_result[ "id" ],
		"type": "warmer_trigger",
		"name": warmer_trigger_name,
		"arn": warmer_trigger_result[ "arn" ]
	})
	
	# Go through all the Lambdas deployed and make them the targets of the
	# warmer Lambda so everything is kept hot.
	# Additionally we'll invoke them all once with a warmup request so
	# that they are hot if hit immediately
	for deployed_lambda in combined_warmup_list:
		yield local_tasks.add_rule_target(
			credentials,
			warmer_trigger_name,
			deployed_lambda[ "name" ],
			deployed_lambda[ "arn" ],
			json.dumps({
				"_refinery": {
					"warmup": warmup_concurrency_level,
				}
			})
		)
		
		local_tasks.warm_up_lambda(
			credentials,
			deployed_lambda[ "arn" ],
			warmup_concurrency_level
		)
	
@gen.coroutine
def add_auto_warmup( credentials, warmup_concurrency_level, unique_deploy_id, combined_warmup_list, diagram_data ):
	# Split warmup list into a list of lists with each list containing five elements.
	# This is so that we match the limit for CloudWatch Rules max targets (5 per rule).
	# See "Targets" under this following URL:
	# https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/cloudwatch_limits_cwe.html
	split_combined_warmup_list = split_list_into_chunks(
		combined_warmup_list,
		5
	)

	# Ensure each Cloudwatch Rule has a unique name
	warmup_unique_counter = 0

	warmup_futures = []

	for warmup_chunk_list in split_combined_warmup_list:
		warmup_futures.append(
			create_warmer_for_lambda_set(
				credentials,
				warmup_concurrency_level,
				unique_deploy_id + "_W" + str( warmup_unique_counter ),
				warmup_chunk_list,
				diagram_data
			)
		)

		warmup_unique_counter += 1

	# Wait for all of the concurrent Cloudwatch Rule creations to finish
	yield warmup_futures
		
class SavedBlocksCreate( BaseHandler ):
	@authenticated
	def post( self ):
		"""
		Create a saved block to import into other projects.
		"""
		schema = {
			"type": "object",
			"properties": {
				"id": {
					"type": "string"
				},
				"description": {
					"type": "string"
				},
				"block_object": {
					"type": "object",
					"properties": {
						"name": {
							"type": "string",
						},
						"type": {
							"type": "string",
						}
					},
					"required": [
						"name",
						"type"
					]
				},
				"version": {
					"type": "integer",
				},
				"share_status": {
					"type": "string",
					"enum": [
						"PRIVATE",
						"PUBLISHED"
					]
				},
				"shared_files": {
					"type": "array",
					"default": [],

				}
			},
			"required": [
				"block_object"
			]
		}
		
		validate_schema( self.json, schema )
		logit( "Saving Block data..." )
		
		saved_block = None

		block_version = 1
		
		if "id" in self.json:
			saved_block = self.dbsession.query( SavedBlock ).filter_by(
				user_id=self.get_authenticated_user_id(),
				id=self.json[ "id" ]
			).first()
			
			# If we didn't find the block return an error
			if not saved_block:
				self.write({
					"success": False,
					"code": "SAVED_BLOCK_NOT_FOUND",
					"msg": "The saved block you're attempting to save could not be found!"
				})
				return
			
			block_version = saved_block.versions
		
		# If the block ID is not specified then we are creating
		# a new saved block in the database.
		if not saved_block:
			saved_block = SavedBlock()
			saved_block.share_status = "PRIVATE"
		
		saved_block.user_id = self.get_authenticated_user_id()
		saved_block.name = self.json[ "block_object" ][ "name" ]
		saved_block.type = self.json[ "block_object" ][ "type" ]
		saved_block.description = ""
		
		if "description" in self.json:
			saved_block.description = self.json[ "description" ]
			
		new_share_status = saved_block.share_status
		
		if "share_status" in self.json:
			new_share_status = self.json[ "share_status" ]
		
		# Ensure that a user can only make a PRIVATE saved block PUBLISHER
		# We don't allow the other way around
		if saved_block.share_status == "PUBLISHED" and new_share_status == "PRIVATE":
			self.write({
				"success": False,
				"code": "CANNOT_UNPUBLISH_SAVED_BLOCKS",
				"msg": "You cannot un-publish an already-published block!"
			})
			return
		
		saved_block.share_status = new_share_status
			
		self.dbsession.commit()
			
		# Get the latest saved block version
		saved_block_latest_version = self.dbsession.query( SavedBlockVersion ).filter_by(
			saved_block_id=saved_block.id
		).order_by( SavedBlockVersion.version.desc() ).first()
		
		# If we have an old version bump it
		if saved_block_latest_version:
			block_version = saved_block_latest_version.version + 1
		
		# Now we add the block version
		new_saved_block_version = SavedBlockVersion()
		new_saved_block_version.saved_block_id = saved_block.id
		new_saved_block_version.version = block_version
		new_saved_block_version.block_object_json = self.json[ "block_object" ]
		new_saved_block_version.shared_files = self.json[ "shared_files" ]
			
		saved_block.versions.append(
			new_saved_block_version
		)
			
		self.dbsession.add( saved_block )
		self.dbsession.commit()
		
		self.write({
			"success": True,
			"block": {
				"id": saved_block.id,
				"description": saved_block.description,
				"name": saved_block.name,
				"share_status": new_share_status,
				"type": saved_block.type,
				"block_object": new_saved_block_version.block_object_json,
				"version": new_saved_block_version.version,
				"timestamp": new_saved_block_version.timestamp
			}
		})


def generate_saved_block_filters(share_status, block_language, search_string, authenticated_user_id):
	# filters to apply when searching for saved blocks
	saved_block_filters = []

	if search_string != "":
		saved_block_filters.append(
			sql_or(
				SavedBlock.name.ilike( "%" + search_string + "%" ),
				SavedBlock.description.ilike( "%" + search_string + "%" ),
			)
		)

	if authenticated_user_id != None:
		# Default is to just search your own saved blocks
		saved_block_filters.append(
			SavedBlock.user_id == authenticated_user_id
		)

	if share_status == "PUBLISHED" or authenticated_user_id == None:
		saved_block_filters.append(
			SavedBlock.share_status == "PUBLISHED"
		)

	if block_language != "":
		saved_block_filters.append(
			SavedBlockVersion.block_object_json[ "language" ].astext == block_language
		)

	return saved_block_filters

class SavedBlockSearch( BaseHandler ):
	def post( self ):
		"""
		Free text search of saved Lambda, returns matching results.
		"""
		schema = {
			"type": "object",
			"properties": {
				"search_string": {
					"type": "string",
				},
				"share_status": {
					"type": "string",
					"enum": [
						"PRIVATE",
						"PUBLISHED"
					]
				},
				"language": {
					"type": "string",
				}
			},
			"required": [
				"search_string",
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Searching saved Blocks..." )
		
		share_status = "PRIVATE"
		block_language = ""
		search_string = ""
		
		if "share_status" in self.json:
			share_status = self.json[ "share_status" ]

		if "language" in self.json:
			block_language = self.json[ "language" ]

		if "search_string" in self.json:
			search_string = self.json[ "search_string" ]

		authenticated_user_id = self.get_authenticated_user_id()

		saved_block_filters = generate_saved_block_filters(
			share_status, block_language, search_string, authenticated_user_id
		)

		# Search through all published saved blocks
		saved_blocks = self.dbsession.query( SavedBlock ).join(
			# join the saved block and version tables based on IDs
			SavedBlockVersion, SavedBlock.id == SavedBlockVersion.saved_block_id
		).filter(
			*saved_block_filters
		).limit(25).all()
		
		return_list = []
		
		for saved_block in saved_blocks:
			# Get the latest saved block version
			saved_block_latest_version = self.dbsession.query( SavedBlockVersion ).filter_by(
				saved_block_id=saved_block.id
			).order_by( SavedBlockVersion.version.desc() ).first()

			block_object = saved_block_latest_version.block_object_json
			block_object[ "id" ] = str( uuid.uuid4() )
			
			return_list.append({
				"id": saved_block.id,
				"description": saved_block.description,
				"name": saved_block.name,
				"share_status": saved_block.share_status,
				"type": saved_block.type,
				"block_object": block_object,
				"version": saved_block_latest_version.version,
				"shared_files": saved_block_latest_version.shared_files,
				"timestamp": saved_block_latest_version.timestamp,
			})
		
		self.write({
			"success": True,
			"results": return_list
		})


class SavedBlockStatusCheck( BaseHandler ):
	@authenticated
	def post( self ):
		"""
		Given a list of blocks, return metadata about them.
		"""
		schema = {
			"type": "object",
			"properties": {
				"block_ids": {
					"type": "array",
					"items": {
						"type": "string"
					},
					"minItems": 1,
					"maxItems": 100
				}
			},
			"required": [
				"block_ids",
			]
		}

		validate_schema( self.json, schema )

		logit( "Fetching saved Block metadata..." )

		# Search through all published saved blocks
		saved_blocks = self.dbsession.query( SavedBlock ).filter(
			SavedBlock.id.in_(self.json[ "block_ids" ]),
			sql_or(
				SavedBlock.user_id == self.get_authenticated_user_id(),
				SavedBlock.share_status == "PUBLISHED"
			)
		).limit(100).all()

		return_list = []

		for saved_block in saved_blocks:
			# Get the latest saved block version
			saved_block_latest_version = self.dbsession.query( SavedBlockVersion ).filter_by(
				saved_block_id=saved_block.id
			).order_by( SavedBlockVersion.version.desc() ).first()

			block_object = saved_block_latest_version.block_object_json

			return_list.append({
				"id": saved_block.id,
				"is_block_owner": saved_block.user_id == self.get_authenticated_user_id(),
				"description": saved_block.description,
				"name": saved_block.name,
				"share_status": saved_block.share_status,
				"version": saved_block_latest_version.version,
				"timestamp": saved_block_latest_version.timestamp,
				"block_object": block_object,
			})

		self.write({
			"success": True,
			"results": return_list
		})


class SavedBlockDelete( BaseHandler ):
	@authenticated
	def delete( self ):
		"""
		Delete a saved Block
		"""
		schema = {
			"type": "object",
			"properties": {
				"id": {
					"type": "string",
				}
			},
			"required": [
				"id"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Deleting Block data..." )
		
		saved_block = self.dbsession.query( SavedBlock ).filter_by(
			user_id=self.get_authenticated_user_id(),
			id=self.json[ "id" ]
		).first()
		
		if saved_block.share_status == "PUBLISHED":
			self.write({
				"success": False,
				"msg": "You cannot delete an already-published block!",
				"code": "ERROR_CANNOT_DELETE_PUBLISHED_BLOCK"
			})
			return
		
		if saved_block == None:
			self.write({
				"success": False,
				"msg": "This block does not exist!",
				"code": "BLOCK_NOT_FOUND"
			})
			return
		
		self.dbsession.delete(saved_block)
		self.dbsession.commit()
		
		self.write({
			"success": True
		})

class InfraTearDown( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		teardown_nodes = self.json[ "teardown_nodes" ]
		
		credentials = self.get_authenticated_user_cloud_configuration()

		teardown_operation_results = yield teardown_infrastructure(
			credentials,
			teardown_nodes
		)
		
		# Delete our logs
		# No need to yield till it completes
		delete_logs(
			credentials,
			self.json[ "project_id" ]
		)
		
		self.write({
			"success": True,
			"result": teardown_operation_results
		})
	
class InfraCollisionCheck( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		logit( "Checking for production collisions..." )
		
		diagram_data = json.loads( self.json[ "diagram_data" ] )
		
		credentials = self.get_authenticated_user_cloud_configuration()
		
		"""
		Returned collisions format:
		
		[
			{
				"id": {{node_id}},
				"arn": {{production_resource_arn}},
				"name": {{node_name}},
				"type": {{node_type}},
			}
		]
		"""
		collision_check_futures = []
		
		"""
		Iterate through workflow states and check for collisions
		for each node in production based off get_lambda_safe_name
		"""
		for workflow_state in diagram_data[ "workflow_states" ]:
			# Check for Lambda collision
			if workflow_state[ "type" ] == "lambda":
				collision_check_futures.append(
					local_tasks.get_aws_lambda_existence_info(
						credentials,
						workflow_state[ "id" ],
						workflow_state[ "type" ],
						get_lambda_safe_name(
							workflow_state[ "name" ]
						)
					)
				)
			# Check for Schedule Trigger collisions (CloudWatch)
			elif workflow_state[ "type" ] == "schedule_trigger":
				collision_check_futures.append(
					local_tasks.get_cloudwatch_existence_info(
						credentials,
						workflow_state[ "id" ],
						workflow_state[ "type" ],
						get_lambda_safe_name(
							workflow_state[ "name" ]
						)
					)
				)
			elif workflow_state[ "type" ] == "sqs_queue":
				collision_check_futures.append(
					local_tasks.get_sqs_existence_info(
						credentials,
						workflow_state[ "id" ],
						workflow_state[ "type" ],
						get_lambda_safe_name(
							workflow_state[ "name" ]
						)
					)
				)
			elif workflow_state[ "type" ] == "sns_topic":
				collision_check_futures.append(
					local_tasks.get_sns_existence_info(
						credentials,
						workflow_state[ "id" ],
						workflow_state[ "type" ],
						get_lambda_safe_name(
							workflow_state[ "name" ]
						)
					)
				)
		
		# Wait for all collision checks to finish
		collision_check_results = yield collision_check_futures
		
		self.write({
			"success": True,
			"result": collision_check_results
		})


class RenameProject( BaseHandler ):
	@authenticated
	def post( self ):
		"""
		Rename a project
		"""
		schema = {
			"type": "object",
			"properties": {
				"project_id": {
					"type": "string"
				},
				"name": {
					"type": "string"
				}
			},
			"required": [
				"project_id",
				"name"
			]
		}

		validate_schema( self.json, schema )

		project_id = self.json[ "project_id" ]
		project_name = self.json[ "name" ]

		if not self.is_owner_of_project( project_id ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have the permissions required to save this project."
			})
			return

		# Grab the project from the database by ID
		previous_project = self.dbsession.query( Project ).filter_by(
			id=project_id
		).first()

		# Verify project exists
		if previous_project is None:
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have the permissions required to save this project."
			})
			return

		# Check if a project already exists with this name
		for project in self.get_authenticated_user().projects:
			if project.name == project_name:
				self.write({
					"success": False,
					"code": "PROJECT_NAME_EXISTS",
					"msg": "A project with this name already exists!"
				})
				return

		# Grab the latest version of the project
		latest_project_version = self.dbsession.query( ProjectVersion ).filter_by(
			project_id=project_id
		).order_by( ProjectVersion.version.desc() ).first()

		# If there is not a latest version of the project, fail out
		if latest_project_version == None:
			self.write({
				"success": False,
				"code": "MISSING_PROJECT",
				"msg": "Unable to locate project data to rename"
			})
			return

		# Generate a new version for the project
		project_version = ( latest_project_version.version + 1 )

		project_json = json.loads(
			latest_project_version.project_json
		)
		project_json[ "name" ] = project_name

		# Save the updated JSON
		latest_project_version.project_json = json.dumps( project_json )
		latest_project_version.version = project_version

		# Write the name to the project table as well (de-normalized)
		previous_project.name = project_name

		# Save the data to the database
		self.dbsession.commit()

		self.write({
			"success": True,
			"code": "RENAME_SUCCESSFUL",
			"msg": "Project renamed successfully"
		})
		return


class SaveProject( BaseHandler ):
	@authenticated
	def post( self ):
		"""
		{
			"project_id": {{project id uuid}} || False # If False create a new project
			"diagram_data": {{diagram_data}},
			"version": "1.0.0" || False # Either specific or just increment
			"config": {{project_config_data}} # Project config such as ENV variables, etc.
		}
		
		TODO:
			* The logic for each branch of project exists and project doesn't exist should be refactored
		"""
		logit( "Saving project to database..." )
		
		project_id = self.json[ "project_id" ]
		diagram_data = json.loads( self.json[ "diagram_data" ] )
		project_name = diagram_data[ "name" ]
		project_version = self.json[ "version" ]
		project_config = self.json[ "config" ]
		
		# If this is a new project and the name already exists
		# Throw an error to indicate this can't be the case
		if project_id == False:
			for project in self.get_authenticated_user().projects:
				if project.name == project_name:
					self.write({
						"success": False,
						"code": "PROJECT_NAME_EXISTS",
						"msg": "A project with this name already exists!"
					})
					return
		
		# Check if project already exists
		if project_id:
			previous_project = self.dbsession.query( Project ).filter_by(
				id=project_id
			).first()
		else:
			previous_project = None
			
		# If a previous project exists, make sure the user has permissions
		# to actually modify it
		if previous_project:
			# Deny if they don't have access
			if not self.is_owner_of_project( project_id ):
				self.write({
					"success": False,
					"code": "ACCESS_DENIED",
					"msg": "You do not have the permissions required to save this project."
				})
				return
		
		# If there is a previous project and the name doesn't match, update it.
		if previous_project and previous_project.name != project_name:
			# Double check that the project name isn't already in use.
			for project in self.get_authenticated_user().projects:
				if project.name == project_name:
					self.write({
						"success": False,
						"code": "PROJECT_NAME_EXISTS",
						"msg": "Name is already used by another project."
					})
					return

			previous_project.name = project_name
			self.dbsession.commit()
		
		# If there's no previous project, create a new one
		if previous_project == None:
			previous_project = Project()
			previous_project.name = diagram_data[ "name" ]
			
			# Add the user to the project so they can access it
			previous_project.users.append(
				self.authenticated_user
			)
			
			self.dbsession.add( previous_project )
			self.dbsession.commit()
			
			# Set project ID to newly generated ID
			project_id = previous_project.id
		
		# If project version isn't set we'll update it to be an incremented version
		# from the latest saved version.
		if project_version == False:
			latest_project_version = self.dbsession.query( ProjectVersion ).filter_by(
				project_id=project_id
			).order_by( ProjectVersion.version.desc() ).first()

			if latest_project_version == None:
				project_version = 1
			else:
				project_version = ( latest_project_version.version + 1 )
		else:
			previous_project_version = self.dbsession.query( ProjectVersion ).filter_by(
				project_id=project_id,
				version=project_version,
			).first()

			# Delete previous version with same ID since we're updating it
			if previous_project_version != None:
				self.dbsession.delete( previous_project_version )
				self.dbsession.commit()
		
		# Now save new project version
		new_project_version = ProjectVersion()
		new_project_version.version = project_version
		new_project_version.project_json = json.dumps(
			diagram_data
		)
		
		previous_project.versions.append(
			new_project_version
		)
		
		# Update project config
		update_project_config(
			self.dbsession,
			project_id,
			project_config
		)
		
		self.write({
			"success": True,
			"project_id": project_id,
			"project_version": project_version
		})
	
class SaveProjectConfig( BaseHandler ):
	@authenticated
	def post( self ):
		"""
		{
			"project_id": {{project id uuid}} || False # If False create a new project
			"config": {{project_config_data}} # Project config such as ENV variables, etc.
		}
		
		TODO:
			* The logic for each branch of project exists and project doesn't exist should be refactored
		"""
		logit( "Saving project config to database..." )
		
		project_id = self.json[ "project_id" ]
		project_config = self.json[ "config" ]
		
		# Deny if they don't have access
		if not self.is_owner_of_project( project_id ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have the permissions required to save this project config."
			})
			return
		
		# Update project config
		update_project_config(
			self.dbsession,
			project_id,
			project_config
		)
		
		self.write({
			"success": True,
			"project_id": project_id,
		})
		
def update_project_config( dbsession, project_id, project_config ):
	# Convert to JSON if not already
	if type( project_config ) == dict:
		project_config = json.dumps(
			project_config
		)
	
	# Check to see if there's a previous project config
	previous_project_config = dbsession.query( ProjectConfig ).filter_by(
		project_id=project_id
	).first()
	
	# If not, create one
	if previous_project_config == None:
		new_project_config = ProjectConfig()
		new_project_config.project_id = project_id
		new_project_config.config_json = project_config
		dbsession.add( new_project_config )
	else: # Otherwise update the current config
		previous_project_config.project_id = project_id
		previous_project_config.config_json = project_config
	
	dbsession.commit()
		
class SearchSavedProjects( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Free text search of saved functions, returns matching results.
		"""
		schema = {
			"type": "object",
			"properties": {
				"query": {
					"type": "string",
				}
			},
			"required": [
				"query",
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Searching saved projects..." )
		
		authenticated_user = self.get_authenticated_user()
		
		# Projects that match the query
		project_search_results = []

		# Project IDs which we'll use in querying for matching deployments
		project_ids = []
		
		# This is extremely inefficient and needs to be fixed to do it in SQL.
		# My fault hacking it this way for YC :)
		for project_data in authenticated_user.projects:
			if self.json[ "query" ].lower() in str( project_data.name ).lower():
				project_search_results.append(
					project_data
				)
				project_ids.append(
					project_data.id
				)
		
		results_list = []

		# Pull all deployments in a batch SQL query
		deployments_list = self.get_batch_project_deployments(
			project_ids
		)
		
		for project_search_result in project_search_results:
			matching_deployment = self.get_deployment_if_in_list(
				project_search_result.id,
				deployments_list
			)

			project_item = {
				"id": project_search_result.id,
				"name": project_search_result.name,
				"timestamp": project_search_result.timestamp,
				"deployment": matching_deployment,
				"versions": []
			}
			
			for project_version in project_search_result.versions:
				project_version_data = self.fetch_project_by_version(project_search_result.id, project_version.version)

				# Skip any invalid project versions, since we can't get the diagram data anyway...
				if project_version_data is None:
					continue

				project_item[ "versions" ].append({
					"timestamp": project_version_data.timestamp,
					"version": project_version.version
				})
				
			# Sort project versions highest to lowest
			project_item[ "versions" ].sort( reverse=True )
			
			results_list.append(
				project_item
			)
		
		self.write({
			"success": True,
			"results": results_list
		})

	def get_deployment_if_in_list( self, project_id, deployments_list ):
		"""
		Checks passed-in list of deployments for one that matches
		the specified project ID. If one exists it'll return it, otherwise
		it will return None (null).
		"""
		for deployment in deployments_list:
			if deployment[ "project_id" ] == project_id:
				return deployment[ "id" ]
		
		return None

	def get_batch_project_deployments( self, project_ids ):
		"""
		Batch up the project deployment lookups so it's fast.
		"""
		deployments = self.dbsession.query( Deployment ).filter(
			# If the deployment matches any of the project IDs we've enumerated
			sql_or(
				*[Deployment.project_id == project_id for project_id in project_ids]
			)
		).order_by(
			Deployment.timestamp.desc()
		).all()

		deployment_dicts = []

		for deployment in deployments:
			if deployment:
				deployment_dicts.append(
					deployment.to_dict()
				)

		return deployment_dicts

	def fetch_project_by_version( self, id, version ):
		project_version_result = self.dbsession.query( ProjectVersion ).filter_by(
			project_id=id,
			version=version
		).first()

		return project_version_result


class GetSavedProject( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Get a specific saved project
		"""
		schema = {
			"type": "object",
			"properties": {
				"project_id": {
					"type": "string",
				},
				"version": {
					"type": "integer",
				}
			},
			"required": [
				"project_id"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Retrieving saved project..." )

		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "project_id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to access that project version!",
			})
			raise gen.Return()
			
		project = self.fetch_project()

		self.write({
			"success": True,
			"project_id": project.project_id,
			"version": project.version,
			"project_json": project.project_json
		})

	def fetch_project( self ):
		if 'version' not in self.json:
			return self.fetch_project_without_version(self.json[ "project_id" ])

		return self.fetch_project_by_version(self.json[ "project_id" ], self.json[ "version" ])

	def fetch_project_by_version( self, id, version ):
		project_version_result = self.dbsession.query( ProjectVersion ).filter_by(
			project_id=id,
			version=version
		).first()

		return project_version_result

	def fetch_project_without_version( self, id ):
		project_version_result = self.dbsession.query( ProjectVersion ).filter_by(
			project_id=id
		).order_by(ProjectVersion.version.desc()).first()

		return project_version_result

class DeleteSavedProject( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Get a specific saved project
		"""
		schema = {
			"type": "object",
			"properties": {
				"id": {
					"type": "string",
				}
			},
			"required": [
				"id"
			]
		}
		
		validate_schema( self.json, schema )
		project_id = self.json[ "id" ]

		logit( "Deleting saved project..." )

		# Ensure user is owner of the project
		if not self.is_owner_of_project( project_id ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to delete that project!",
			})
			raise gen.Return()

		credentials = self.get_authenticated_user_cloud_configuration()

		# Pull the latest project config
		project_config = self.dbsession.query( ProjectConfig ).filter_by(
			project_id=project_id
		).first()

		if project_config is not None:
			self.delete_api_gateway(project_config)

		# delete all AWS deployments
		deployed_projects = self.dbsession.query( Deployment ).filter_by(
			project_id=project_id
		).all()
		for deployment in deployed_projects:
			# load deployed project workflow states
			deployment_json = json.loads(deployment.deployment_json)

			if "workflow_states" not in deployment_json:
				raise Exception("Corrupt deployment JSON data read from database, missing workflow_states for teardown")

			teardown_nodes = deployment_json[ "workflow_states" ]

			# do the teardown of the deployed aws infra
			teardown_operation_results = yield teardown_infrastructure(
				credentials,
				teardown_nodes
			)

		# delete existing logs for the project
		delete_logs(
			credentials,
			project_id
		)

		saved_project_result = self.dbsession.query( Project ).filter_by(
			id=project_id
		).first()
		
		self.dbsession.delete( saved_project_result )
		self.dbsession.commit()

		self.write({
			"success": True
		})

	def delete_api_gateway( self, project_config ):
		credentials = self.get_authenticated_user_cloud_configuration()
		project_config_data = project_config.to_dict()
		project_config_dict = project_config_data[ "config_json" ]

		# Delete the API Gateway associated with this project
		if "api_gateway" in project_config_dict:
			api_gateway_id = project_config_dict[ "api_gateway" ][ "gateway_id" ]

			if api_gateway_id:
				logit( "Deleting associated API Gateway '" + api_gateway_id + "'..." )

				yield api_gateway_manager.delete_rest_api(
					credentials,
					api_gateway_id
				)

class DeployDiagram( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		# TODO: Add jsonschema
		logit( "Deploying diagram to production..." )
		
		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "project_id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to deploy that!",
			})
			raise gen.Return()
		
		project_id = self.json[ "project_id" ]
		project_name = self.json[ "project_name" ]
		project_config = self.json[ "project_config" ]
		
		diagram_data = json.loads( self.json[ "diagram_data" ] )
		
		credentials = self.get_authenticated_user_cloud_configuration()

		deployment_data = yield deploy_diagram(
			credentials,
			project_name,
			project_id,
			diagram_data,
			project_config
		)
		
		# Check if the deployment failed
		if deployment_data[ "success" ] == False:
			logit( "We are now rolling back the deployments we've made...", "error" )
			yield teardown_infrastructure(
				credentials,
				deployment_data[ "teardown_nodes_list" ]
			)
			logit( "We've completed our rollback, returning an error...", "error" )
			
			# For now we'll just raise
			self.write({
				"success": True, # Success meaning we caught it
				"result": {
					"deployment_success": False,
					"exceptions": deployment_data[ "exceptions" ],
				}
			})
			raise gen.Return()
		
		# TODO: Update the project data? Deployments should probably
		# be an explicit "Save Project" action.
		
		existing_project = self.dbsession.query( Project ).filter_by(
			id=project_id
		).first()
		
		new_deployment = Deployment()
		new_deployment.project_id = project_id
		new_deployment.deployment_json = json.dumps(
			deployment_data[ "deployment_diagram" ]
		)
		
		existing_project.deployments.append(
			new_deployment
		)
		
		self.dbsession.commit()
		
		# Update project config
		logit( "Updating database with new project config..." )
		update_project_config(
			self.dbsession,
			project_id,
			deployment_data[ "project_config" ]
		)
		
		self.write({
			"success": True,
			"result": {
				"deployment_success": True,
				"diagram_data": deployment_data[ "deployment_diagram" ],
				"project_id": project_id,
				"deployment_id": new_deployment.id,
			}
		})
		
class GetProjectConfig( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Get the project config for a given project ID
		"""
		schema = {
			"type": "object",
			"properties": {
				"project_id": {
					"type": "string",
				}
			},
			"required": [
				"project_id"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Retrieving project deployments..." )
		
		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "project_id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to get that project version!",
			})
			raise gen.Return()
		
		project_config = self.dbsession.query( ProjectConfig ).filter_by(
			project_id=self.json[ "project_id" ]
		).first()
		
		project_config_data = project_config.to_dict()

		self.write({
			"success": True,
			"result": project_config_data[ "config_json" ]
		})
		
class GetLatestProjectDeployment( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Get latest deployment for a given project ID
		"""
		schema = {
			"type": "object",
			"properties": {
				"project_id": {
					"type": "string",
				}
			},
			"required": [
				"project_id"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Retrieving project deployments..." )
		
		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "project_id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to get this project deployment!",
			})
			raise gen.Return()
		
		latest_deployment = self.dbsession.query( Deployment ).filter_by(
			project_id=self.json[ "project_id" ]
		).order_by(
			Deployment.timestamp.desc()
		).first()
		
		result_data = False
		
		if latest_deployment:
			result_data = latest_deployment.to_dict()

		self.write({
			"success": True,
			"result": result_data
		})
		
class DeleteDeploymentsInProject( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Delete all deployments in database for a given project
		"""
		schema = {
			"type": "object",
			"properties": {
				"project_id": {
					"type": "string",
				}
			},
			"required": [
				"project_id"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Deleting deployments from database..." )
		
		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "project_id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to delete that deployment!",
			})
			raise gen.Return()
		
		deployment = self.dbsession.query( Deployment ).filter_by(
			project_id=self.json[ "project_id" ]
		).first()
		
		if deployment:
			self.dbsession.delete(deployment)
			self.dbsession.commit()
		
		# Delete the cached shards in the database
		self.dbsession.query(
			CachedExecutionLogsShard
		).filter(
			CachedExecutionLogsShard.project_id==self.json[ "project_id" ]
		).delete()
		self.dbsession.commit()
		
		self.write({
			"success": True
		})
	
@gen.coroutine
def create_lambda_api_route( credentials, api_gateway_id, http_method, route, lambda_name, overwrite_existing ):
	def not_empty( input_item ):
		return ( input_item != "" )
	path_parts = route.split( "/" )
	path_parts = filter( not_empty, path_parts )
	
	# First we clean the Lambda of API Gateway policies which point
	# to dead API Gateways
	yield local_tasks.clean_lambda_iam_policies(
		credentials,
		lambda_name
	)
	
	# A default resource is created along with an API gateway, we grab
	# it so we can make our base method
	resources = yield api_gateway_manager.get_resources(
		credentials,
		api_gateway_id
	)
	
	for resource in resources:
		if resource[ "path" ] == "/":
			base_resource_id = resource[ "id" ]
			break
	
	# Create a map of paths to verify existance later
	# so we don't overwrite existing resources
	path_existence_map = {}
	for resource in resources:
		path_existence_map[ resource[ "path" ] ] = resource[ "id" ]
	
	# Set the pointer to the base
	current_base_pointer_id = base_resource_id
	
	# Path level, continously updated
	current_path = ""
	
	# Create entire path from chain
	for path_part in path_parts:
		"""
		TODO: Check for conflicting resources and don't
		overwrite an existing resource if it exists already.
		"""
		# Check if there's a conflicting resource here
		current_path = current_path + "/" + path_part
		
		# Get existing resource ID instead of creating one
		if current_path in path_existence_map:
			current_base_pointer_id = path_existence_map[ current_path ]
		else:
			# Otherwise go ahead and create one
			new_resource = yield local_tasks.create_resource(
				credentials,
				api_gateway_id,
				current_base_pointer_id,
				path_part
			)
			
			current_base_pointer_id = new_resource[ "id" ]
	
	# Create method on base resource
	method_response = yield local_tasks.create_method(
		credentials,
		"HTTP Method",
		api_gateway_id,
		current_base_pointer_id,
		http_method,
		False,
	)
	
	# Link the API Gateway to the lambda
	link_response = yield local_tasks.link_api_method_to_lambda(
		credentials,
		api_gateway_id,
		current_base_pointer_id,
		http_method, # GET was previous here
		route,
		lambda_name
	)
	
	resources = yield api_gateway_manager.get_resources(
		credentials,
		api_gateway_id
	)
	
	# Clown-shoes AWS bullshit for binary response
	yield local_tasks.add_integration_response(
		credentials,
		api_gateway_id,
		current_base_pointer_id,
		http_method,
		lambda_name
	)
	
@gen.coroutine
def get_cloudflare_keys():
	"""
	Get keys to validate inbond JWTs
	"""
	global CF_ACCESS_PUBLIC_KEYS
	CF_ACCESS_PUBLIC_KEYS = []
	
	# Update public keys every hour
	public_keys_update_interval = (
		60 * 60 * 1
	)
	
	logit( "Requesting Cloudflare's Access keys for '" + os.environ.get( "cf_certs_url" ) + "'..." )
	client = AsyncHTTPClient()
	
	request = HTTPRequest(
		url=os.environ.get( "cf_certs_url" ),
		method="GET",
	)
	
	response = yield client.fetch(
		request
	)
	
	response_data = json.loads(
		response.body
	)
	
	for key_dict in response_data[ "keys" ]:
		public_key = jwt.algorithms.RSAAlgorithm.from_jwk(
			json.dumps(
				key_dict
			)
		)
		CF_ACCESS_PUBLIC_KEYS.append(
			public_key
		)
	
	logit( "Private keys to be updated again in " + str( public_keys_update_interval ) + " second(s)..." )
	tornado.ioloop.IOLoop.current().add_timeout(
		time.time() + public_keys_update_interval,
		get_cloudflare_keys
	)
	
@gen.coroutine
def load_further_partitions( credentials, project_id, new_shards_list ):
	project_id = re.sub( REGEX_WHITELISTS[ "project_id" ], "", project_id )
	
	query_template = "ALTER TABLE PRJ_{{PROJECT_ID_REPLACE_ME}} ADD IF NOT EXISTS\n"
	
	query = query_template.replace(
		"{{PROJECT_ID_REPLACE_ME}}",
		project_id.replace(
			"-",
			"_"
		)
	)
	
	for new_shard in new_shards_list:
		query += "PARTITION (dt = '" + new_shard.replace( "dt=", "" ) + "') "
		query += "LOCATION 's3://" + credentials[ "logs_bucket" ] + "/"
		query += project_id + "/" + new_shard + "/'\n"
	
	logit( "Updating previously un-indexed partitions... ", "debug" )
	yield local_tasks.perform_athena_query(
		credentials,
		query,
		False
	)
	
@gen.coroutine
def update_athena_table_partitions( credentials, project_id ):
	"""
	Check all the partitions that are in the Athena project table and
	check S3 to see if there are any partitions which need to be added to the
	table. If there are then kick off a query to load the new partitions.
	"""
	project_id = re.sub( REGEX_WHITELISTS[ "project_id" ], "", project_id )
	query_template = "SHOW PARTITIONS PRJ_{{PROJECT_ID_REPLACE_ME}}"
	
	query = query_template.replace(
		"{{PROJECT_ID_REPLACE_ME}}",
		project_id.replace(
			"-",
			"_"
		)
	)
	
	logit( "Retrieving table partitions... ", "debug" )
	results = yield local_tasks.perform_athena_query(
		credentials,
		query,
		True
	)
	
	athena_known_shards = []
	
	for result in results:
		for key, shard_string in result.iteritems():
			if not ( shard_string in athena_known_shards ):
				athena_known_shards.append(
					shard_string
				)
				
	athena_known_shards.sort()
	
	# S3 pulled shards
	s3_pulled_shards = []
	
	continuation_token = False
	
	s3_prefix = project_id + "/"
	
	latest_athena_known_shard = False
	if len( athena_known_shards ) > 0:
		latest_athena_known_shard = s3_prefix + athena_known_shards[-1]
		
	while True:
		s3_list_results = yield local_tasks.get_s3_list_from_prefix(
			credentials,
			credentials[ "logs_bucket" ],
			s3_prefix,
			continuation_token,
			latest_athena_known_shard
		)
		
		s3_shards = s3_list_results[ "common_prefixes" ]
		continuation_token = s3_list_results[ "continuation_token" ]
		
		# Add all new shards to the list
		for s3_shard in s3_shards:
			if not ( s3_shard in s3_pulled_shards ):
				s3_pulled_shards.append(
					s3_shard
				)
				
		# No further to go, we've exhausted the continuation token
		if continuation_token == False:
			break
	
	# The list of shards which have not been imported into Athena
	new_s3_shards = []
	
	for s3_pulled_shard in s3_pulled_shards:
		# Clean it up so it's just dt=2019-07-15-04-45
		s3_pulled_shard = s3_pulled_shard.replace(
			project_id,
			""
		)
		s3_pulled_shard = s3_pulled_shard.replace(
			"/",
			""
		)
		
		if not ( s3_pulled_shard in athena_known_shards ):
			new_s3_shards.append(
				s3_pulled_shard
			)
	
	# If we have new partitions let's load them.
	if len( new_s3_shards ) > 0:
		yield load_further_partitions(
			credentials,
			project_id,
			new_s3_shards
		)
	
	raise gen.Return()
	
def get_five_minute_dt_from_dt( input_datetime ):
	round_to = ( 60 * 5 )
	
	seconds = ( input_datetime.replace( tzinfo=None ) - input_datetime.min ).seconds
	rounding = (
					   seconds + round_to / 2
			   ) // round_to * round_to
	nearest_datetime = input_datetime + datetime.timedelta( 0, rounding - seconds, - input_datetime.microsecond )
	return nearest_datetime
	
def dt_to_shard( input_dt ):
	return input_dt.strftime( "%Y-%m-%d-%H-%M" )
	
def get_execution_metadata_from_s3_key( aws_region, account_id, input_s3_key ):
	# 08757409-4bc8-4a29-ade7-371b1a46f99e/dt=2019-07-15-18-00/e4e3571e-ab59-4790-8072-3049805301c3/SUCCESS~Untitled_Code_Block_RFNItzJNn2~3233e08a-baf0-4f8f-a4c2-ee2d3153f75b~1563213635
	s3_key_parts = input_s3_key.split(
		"/"
	)
	
	log_file_name = s3_key_parts[-1]
	log_file_name_parts = log_file_name.split( "~" )
	
	return_data = {
		"arn": "arn:aws:lambda:" + aws_region + ":" + account_id + ":function:" + log_file_name_parts[1],
		"project_id": s3_key_parts[0],
		"dt": s3_key_parts[1].replace( "dt=", "" ),
		"execution_pipeline_id": s3_key_parts[2],
		"type": log_file_name_parts[0],
		"function_name": log_file_name_parts[1],
		"log_id": log_file_name_parts[2],
		"timestamp": int( log_file_name_parts[3] ),
		"count": "1"
	}
	
	return return_data
	
@gen.coroutine
def get_execution_stats_since_timestamp( credentials, project_id, oldest_timestamp ):
	# Database session for pulling cached data
	dbsession = DBSession()
	
	# Grab a shard dt ten minutes in the future just to make sure
	# we've captured everything appropriately
	newest_shard_dt = get_five_minute_dt_from_dt(
		datetime.datetime.now() + datetime.timedelta(minutes = 5)
	)
	newest_shard_dt_shard = dt_to_shard( newest_shard_dt )
	
	# Shard dt that we can be sure is actually done and the results
	# pulled from S3 can be cached in the database.
	assured_cachable_dt = get_five_minute_dt_from_dt(
		datetime.datetime.now() - datetime.timedelta(minutes = 5)
	)
	assured_cachable_dt_shard = dt_to_shard( assured_cachable_dt )
	
	# Generate the shard dt for the oldest_timestamp
	oldest_shard_dt = get_five_minute_dt_from_dt(
		datetime.datetime.fromtimestamp(
			oldest_timestamp
		)
	)
	oldest_shard_dt_shard = dt_to_shard( oldest_shard_dt )
	
	# Standard S3 prefix before date for all S3 shards
	s3_prefix = project_id + "/dt="
	
	example_shard = s3_prefix + oldest_shard_dt_shard
	
	all_s3_shards = []
	
	common_prefixes = []
	
	continuation_token = False
	
	while True:
		# List shards in the S3 bucket starting at the oldest available shard
		# That's because S3 buckets will start at the oldest time and end at
		# the latest time (due to inverse binary UTF-8 sort order)
		s3_list_results = yield local_tasks.get_s3_list_from_prefix(
			credentials,
			credentials[ "logs_bucket" ],
			s3_prefix,
			continuation_token,
			example_shard
		)
		
		current_common_prefixes = s3_list_results[ "common_prefixes" ]
		continuation_token = s3_list_results[ "continuation_token" ]
		
		# Add all new shards to the list
		for common_prefix in current_common_prefixes:
			if not ( common_prefix in common_prefixes ):
				common_prefixes.append(
					common_prefix
				)
				
		# No further to go, we've exhausted the continuation token
		if continuation_token == False:
			break
	
	for shard_full_path in common_prefixes:
		# Clean it up so it's just dt=2019-07-15-04-45
		shard_full_path = shard_full_path.replace(
			project_id,
			""
		)
		shard_full_path = shard_full_path.replace(
			"/",
			""
		)
		
		if not ( shard_full_path in all_s3_shards ):
			all_s3_shards.append(
				shard_full_path
			)
		
	# Array of all of the metadata for each execution
	"""
	execution_log_results example:
	[
		{
		    "arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn2",
		    "count": "1",
		    "dt": "2019-07-15-13-35",
		    "execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
		    "function_name": "Untitled_Code_Block_RFNItzJNn2",
		    "log_id": "22e4625e-46d1-401a-b935-bcde17f8b667",
		    "project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
		    "timestamp": 1563197795,
		    "type": "SUCCESS"
		}
		{
		    "arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn3",
		    "count": "1",
		    "dt": "2019-07-15-13-35",
		    "execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
		    "function_name": "Untitled_Code_Block_RFNItzJNn3",
		    "log_id": "40b02027-c856-4d2b-bd63-c62f300944e5",
		    "project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
		    "timestamp": 1563197795,
		    "type": "SUCCESS"
		}
	]
	"""
	execution_log_results = []
	
	start_time = time.time()
	
	# Before we do the next step we can save ourselves a lot of time
	# by pulling all of the cached shard data from the database.
	# All of the remaining shards we can go and scan out of S3.
	cached_execution_shards = dbsession.query( CachedExecutionLogsShard ).filter(
		CachedExecutionLogsShard.project_id == project_id
	).filter(
		CachedExecutionLogsShard.date_shard.in_(
			all_s3_shards
		)
	).all()

	logit("--- Pulling shards from database: %s seconds ---" % (time.time() - start_time), "debug" )
	
	# Take the list of cached_execution_shards and remove all of the
	# cached results contained in it from the list of shards we need to
	# go scan S3 for.
	cached_execution_log_results = []
	
	logit(
		"Number of cached shards in the DB we can skip S3 scanning for: " + str( len( cached_execution_shards ) ),
		"debug"
	)
	
	for cached_execution_shard in cached_execution_shards:
		cached_execution_shard_dict = cached_execution_shard.to_dict()
		
		# Add the cached shard data to the cached executions
		cached_execution_log_results = cached_execution_log_results + cached_execution_shard_dict[ "shard_data" ]
		
		# Remove this from the shards to go scan since we already have it
		if cached_execution_shard_dict[ "date_shard" ] in all_s3_shards:
			all_s3_shards.remove( cached_execution_shard_dict[ "date_shard" ] )
		
	logit( "Number of un-cached shards in S3 we have to scan: " + str( len( all_s3_shards ) ), "debug" )
	
	for s3_shard in all_s3_shards:
		full_shard = project_id + "/" + s3_shard
		
		start_time = time.time()
		execution_logs = yield local_tasks.get_s3_pipeline_execution_logs(
			credentials,
			full_shard,
			-1
		)
		logit( "--- Pulling keys from S3: %s seconds ---" % (time.time() - start_time), "debug" )
		
		start_time = time.time()
		for execution_log in execution_logs:
			execution_log_results.append(
				get_execution_metadata_from_s3_key(
					credentials[ "region" ],
					credentials[ "account_id" ],
					execution_log
				)
			)
		logit( "--- Parsing S3 keys: %s seconds ---" % (time.time() - start_time), "debug" )
			
	# We now got over all the execution log results to see what can be cached. The way
	# we do this is we go over each execution log result and we check if the "dt" shard
	# is less than or equal to the time specified in the assured_cachable_dt. If it is,
	# we than add it to our cachable_dict (format below) and at the end we store all of
	# the results in the database so that we never have to pull those shards again.
	"""
	{
		"{{CACHEABLE_DT_SHARD}}": [
			{
			    "arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn2",
			    "count": "1",
			    "dt": "2019-07-15-13-35",
			    "execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
			    "function_name": "Untitled_Code_Block_RFNItzJNn2",
			    "log_id": "22e4625e-46d1-401a-b935-bcde17f8b667",
			    "project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
			    "timestamp": 1563197795,
			    "type": "SUCCESS"
			}
			{
			    "arn": "arn:aws:lambda:us-west-2:532121572788:function:Untitled_Code_Block_RFNItzJNn3",
			    "count": "1",
			    "dt": "2019-07-15-13-35",
			    "execution_pipeline_id": "46b0fdd3-266d-4c6f-af7c-79198a112e96",
			    "function_name": "Untitled_Code_Block_RFNItzJNn3",
			    "log_id": "40b02027-c856-4d2b-bd63-c62f300944e5",
			    "project_id": "08757409-4bc8-4a29-ade7-371b1a46f99e",
			    "timestamp": 1563197795,
			    "type": "SUCCESS"
			}
		]
		"2019-07-15-13-35": "",
	}
	"""
	cachable_dict = {}
	
	for execution_log_result in execution_log_results:
		# Check if dt share is within the cachable range
		current_execution_log_result_dt = execution_log_result[ "dt" ]
		shard_as_dt = datetime.datetime.strptime(
			current_execution_log_result_dt,
			"%Y-%m-%d-%H-%M"
		)
		
		if shard_as_dt <= assured_cachable_dt:
			if not ( current_execution_log_result_dt in cachable_dict ):
				cachable_dict[ current_execution_log_result_dt ] = []
				
			cachable_dict[ current_execution_log_result_dt ].append(
				execution_log_result
			)
			
	# Now we add in the cached shard data
	execution_log_results = execution_log_results + cached_execution_log_results
			
	start_time = time.time()
	execution_pipeline_dict = TaskSpawner._execution_log_query_results_to_pipeline_id_dict(
		execution_log_results
	)
	logit("--- Converting to execution_pipeline_dict: %s seconds ---" % (time.time() - start_time), "debug" )
	
	start_time = time.time()
	frontend_format = TaskSpawner._execution_pipeline_id_dict_to_frontend_format(
		execution_pipeline_dict
	)
	logit("--- Converting to front-end-format: %s seconds ---" % (time.time() - start_time), "debug" )
	
	start_time = time.time()
	# We now store all cachable shard data in the database so we don't have
	# to rescan those shards in S3.
	for date_shard_key, cachable_execution_list in cachable_dict.iteritems():
		new_execution_log_shard = CachedExecutionLogsShard()
		new_execution_log_shard.date_shard = "dt=" + date_shard_key
		new_execution_log_shard.shard_data = cachable_execution_list
		new_execution_log_shard.project_id = project_id
		dbsession.add( new_execution_log_shard )
	
	# Write the cache data to the database
	dbsession.commit()
	dbsession.close()
	logit("--- Caching results in database: %s seconds ---" % (time.time() - start_time), "debug" )
	
	raise gen.Return( frontend_format )

class GetProjectExecutions( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Get past execution ID(s) for a given deployed project
		and their respective metadata.
		"""
		schema = {
			"type": "object",
			"properties": {
				"project_id": {
					"type": "string",
				},
				"oldest_timestamp": {
					"type": "integer"
				}
			},
			"required": [
				"project_id",
				"oldest_timestamp"
			]
		}
		
		validate_schema( self.json, schema )
		
		credentials = self.get_authenticated_user_cloud_configuration()
		
		# We do this to always keep Athena partitioned for the later
		# steps of querying
		update_athena_table_partitions(
			credentials,
			self.json[ "project_id" ]
		)
		
		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "project_id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to access that project's executions!",
			})
			raise gen.Return()
		
		logit( "Pulling the relevant logs for the project ID specified...", "debug" )
		
		# Pull the logs
		execution_pipeline_totals = yield get_execution_stats_since_timestamp(
			credentials,
			self.json[ "project_id" ],
			self.json[ "oldest_timestamp" ]
		)
		
		self.write({
			"success": True,
			"result": execution_pipeline_totals
		})

def chunk_list( input_list, chunk_size ):
	"""
	Chunk an input list into a list of lists
	of size chunk_size. (e.g. 10 lists of size 100)
	"""
	def _chunk_list( input_list, chunk_size ):
		for i in range( 0, len( input_list ), chunk_size ):
			yield input_list[i:i + chunk_size]
	return list(_chunk_list(
		input_list,
		chunk_size
	))
	
@gen.coroutine
def write_remaining_project_execution_log_pages( credentials, data_to_write_list ):
	# How many logs to write to S3 in parallel
	parallel_write_num = 5
	
	# Futures for the writes
	s3_write_futures = []
	
	# Write results to S3
	for i in range( 0, parallel_write_num ):
		if len( data_to_write_list ) == 0:
			break
		
		data_to_write = data_to_write_list.pop(0)
		s3_write_futures.append(
			local_tasks.write_json_to_s3(
				credentials,
				credentials[ "logs_bucket" ],
				data_to_write[ "s3_path" ],
				data_to_write[ "chunked_data" ]
			)
		)
		
		# If we've hit our parallel write number
		# We should yield and wait for the results
		s3_write_futures_number = len( s3_write_futures )
		if s3_write_futures_number >= 5:
			logit( "Writing batch of #" + str( s3_write_futures_number ) + " page(s) of search results to S3..." )
			yield s3_write_futures
			
			# Clear list of futures
			s3_write_futures = []
	
	# If there are remaining futures we need to yield them
	s3_write_futures_number = len( s3_write_futures )
	if s3_write_futures_number > 0:
		logit( "Writing remaining batch of #" + str( s3_write_futures_number ) + " page(s) of search results to S3..." )
		yield s3_write_futures

class GetProjectExecutionLogs( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Get log data for a list of log paths.
		"""
		schema = {
			"type": "object",
			"properties": {
				"execution_pipeline_id": {
					"type": "string",
				},
				"arn": {
					"type": "string",
				},
				"project_id": {
					"type": "string",
				},
				"oldest_timestamp": {
					"type": "integer"
				}
			},
			"required": [
				"arn",
				"execution_pipeline_id",
				"project_id",
				"oldest_timestamp"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Retrieving requested logs..." )
		
		credentials = self.get_authenticated_user_cloud_configuration()

		results = yield local_tasks.get_block_executions(
			credentials,
			self.json[ "project_id" ],
			self.json[ "execution_pipeline_id" ],
			self.json[ "arn" ],
			self.json[ "oldest_timestamp" ]
		)
		
		# Split out shards
		chunked_results = chunk_list(
			results,
			50
		)
		
		# The final return format
		final_return_data = {
			"results": [],
			"pages": []
		}
		
		# Take the first 50 results and stuff it into "results"
		if len( chunked_results ) > 0:
			# Pop first list of list of lists
			final_return_data[ "results" ] = chunked_results.pop(0)
			
		# We batch up the work to do but we don't yield on it until
		# after we write the response. This allows for fast response times
		# and by the time they actually request a later page we've already
		# written it.
		data_to_write_list = []
			
		# Turn the rest into S3 chunks which can be loaded later
		# by the frontend on demand.
		for chunked_result in chunked_results:
			result_uuid = str( uuid.uuid4() )
			s3_path = "log_pagination_result_pages/" + result_uuid + ".json"
			data_to_write_list.append({
				"s3_path": s3_path,
				"chunked_data": chunked_result
			})
			
			# We just add the UUID to the response as if we've
			# already written it
			final_return_data[ "pages" ].append(
				result_uuid
			)
			
		# Clear that memory ASAP
		del chunked_results
		
		self.write({
			"success": True,
			"result": final_return_data
		})
		
		# Write the remaining results
		yield write_remaining_project_execution_log_pages(
			credentials,
			data_to_write_list
		)
			
class GetProjectExecutionLogsPage( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Get a page of results which was previously written in a
		chunk to S3 as JSON. This is to allow lazy-loading of results
		for logs of a given Code Block in an execution ID.
		"""
		schema = {
			"type": "object",
			"properties": {
				"id": {
					"type": "string",
				}
			},
			"required": [
				"id"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Retrieving results page of log results from S3..." )
		
		credentials = self.get_authenticated_user_cloud_configuration()
		
		success = False
		
		# Try grabbing the logs twice because the front-end is being
		# all sensitive again :)
		for i in range( 0, 2 ):
			try:
				results = yield local_tasks.get_json_from_s3(
					credentials,
					credentials[ "logs_bucket" ],
					"log_pagination_result_pages/" + self.json[ "id" ] + ".json"
				)
				success = True
				break
			except Exception, e:
				logit( "Error occurred while reading results page from S3, potentially it's expired?" )
				logit( e )
				results = []
				
			logit( "Retrying again just in case it's not propogated yet..." )
		
		self.write({
			"success": success,
			"result": {
				"results": results
			}
		})
		
class GetProjectExecutionLogObjects( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Return contents of provided list of S3 object paths.
		"""
		schema = {
			"type": "object",
			"properties": {
				"logs_to_fetch": {
					"type": "array",
					"items": {
						"type": "object",
						"properties": {
							"s3_key": {
								"type": "string"
							},
							"log_id": {
								"type": "string"
							}
						},
						"required": ["s3_key", "log_id"]
					},
					"minItems": 1,
					"maxItems": 50
				}
			},
			"required": [
				"logs_to_fetch"
			]
		}

		validate_schema( self.json, schema )

		logit( "Retrieving requested log files..." )

		credentials = self.get_authenticated_user_cloud_configuration()

		results_list = []

		for log_to_fetch in self.json[ "logs_to_fetch" ]:
			s3_key = log_to_fetch[ "s3_key" ]
			log_id = log_to_fetch[ "log_id" ]

			log_data = yield local_tasks.get_json_from_s3(
				credentials,
				credentials[ "logs_bucket" ],
				s3_key
			)

			results_list.append({
				"log_data": log_data,
				"log_id": log_id
			})

		self.write({
			"success": True,
			"result": {
				"results": results_list
			}
		})
		
@gen.coroutine
def delete_logs( credentials, project_id ):
	while True:
		# Delete 1K logs at a time
		log_paths = yield local_tasks.get_s3_pipeline_execution_logs(
			credentials,
			project_id + "/",
			1000
		)
		
		logit( "Deleting #" + str( len( log_paths ) ) + " log files for project ID " + project_id + "..." )

		if len( log_paths ) == 0:
			break
		
		yield local_tasks.bulk_s3_delete(
			credentials,
			credentials[ "logs_bucket" ],
			log_paths
		)

class UpdateEnvironmentVariables( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Update environment variables for a given Lambda.
		
		Save the updated deployment diagram to the database and return
		it to the frontend.
		"""
		schema = {
			"type": "object",
			"properties": {
				"project_id": {
					"type": "string",
				},
				"arn": {
					"type": "string",
				},
				"environment_variables": {
					"type": "array",
				},
				
			},
			"required": [
				"arn",
				"environment_variables"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Updating environment variables..." )
		
		credentials = self.get_authenticated_user_cloud_configuration()
		
		response = yield local_tasks.update_lambda_environment_variables(
			credentials,
			self.json[ "arn" ],
			self.json[ "environment_variables" ],
		)
		
		# Update the deployment diagram to reflect the new environment variables
		latest_deployment = self.dbsession.query( Deployment ).filter_by(
			project_id=self.json[ "project_id" ]
		).order_by(
			Deployment.timestamp.desc()
		).first()
		
		# Get deployment diagram from it
		deployment_diagram_data = json.loads( latest_deployment.deployment_json )
		
		# Get node with the specified ARN and update it
		for workflow_state in deployment_diagram_data[ "workflow_states" ]:
			if workflow_state[ "arn" ] == self.json[ "arn" ]:
				workflow_state[ "environment_variables" ] = self.json[ "environment_variables" ]
		
		latest_deployment.deployment_json = json.dumps( deployment_diagram_data )
		self.dbsession.commit()
		
		self.write({
			"success": True,
			"result": {
				"deployment_diagram": deployment_diagram_data
			}
		})
		
class GetCloudWatchLogsForLambda( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Get CloudWatch Logs for a given Lambda ARN.
		
		The logs may not be complete, since it takes time to propogate.
		"""
		schema = {
			"type": "object",
			"properties": {
				"arn": {
					"type": "string",
				},
				
			},
			"required": [
				"arn"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Retrieving CloudWatch logs..." )
		
		credentials = self.get_authenticated_user_cloud_configuration()
		
		arn = self.json[ "arn" ]
		arn_parts = arn.split( ":" )
		lambda_name = arn_parts[ -1 ]
		log_group_name = "/aws/lambda/" + lambda_name
		
		log_output = yield local_tasks.get_lambda_cloudwatch_logs(
			credentials,
			log_group_name,
			False
		)
		
		truncated = True
		
		if "END RequestId: " in log_output:
			truncated = False
		
		self.write({
			"success": True,
			"result": {
				"truncated": truncated,
				"log_output": log_output
			}
		})

class NewRegistration( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Register a new Refinery account.
		
		This will trigger an email to verify the user's account.
		Email is used for authentication, so by design the user will
		have to validate their email to log into the service.
		"""
		schema = {
			"type": "object",
			"properties": {
				"organization_name": {
					"type": "string",
				},
				"name": {
					"type": "string",
				},
				"email": {
					"type": "string",
				},
				"phone": {
					"type": "string",
				},
				"stripe_token": {
					"type": "string",
				}
			},
			"required": [
				"organization_name",
				"name",
				"email",
				"phone",
				"stripe_token",
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Processing user registration..." )
		
		# Before we continue, check if the email is valid
		try:
			email_validator = validate_email(
				self.json[ "email" ]
			)
			email = email_validator[ "email" ] # replace with normalized form
		except EmailNotValidError as e:
			logit( "Invalid email provided during signup!" )
			self.write({
				"success": False,
				"result": {
					"code": "INVALID_EMAIL",
					"msg": str( e ) # The exception string is user-friendly by design.
				}
			})
			raise gen.Return()
			
		# Create new organization for user
		new_organization = Organization()
		new_organization.name = self.json[ "organization_name" ]
		
		# Set defaults
		new_organization.payments_overdue = False
		
		# Check if the user is already registered
		user = self.dbsession.query( User ).filter_by(
			email=self.json[ "email" ]
		).first()
		
		# If the user already exists, stop here and notify them.
		# They should be given the option to attempt to authenticate/confirm
		# their account by logging in.
		if user != None:
			self.write({
				"success": False,
				"result": {
					"code": "USER_ALREADY_EXISTS",
					"msg": "A user with that email address already exists!"
				}
			})
			raise gen.Return()
		
		# Create the user itself and add it to the organization
		new_user = User()
		new_user.name = self.json[ "name" ]
		new_user.email = self.json[ "email" ]
		new_user.phone_number = self.json[ "phone" ]
		new_user.has_valid_payment_method_on_file = True
		
		# Create a new email auth token as well
		email_auth_token = EmailAuthToken()
		
		# Pull out the authentication token
		raw_email_authentication_token = email_auth_token.token
		
		# Add the token to the list of the user's token
		new_user.email_auth_tokens.append(
			email_auth_token
		)
		
		# Add user to the organization
		new_organization.users.append(
			new_user
		)
		
		# Set this user as the billing admin
		new_organization.billing_admin_id = new_user.id
		
		self.dbsession.add( new_organization )

		# Stash some information about the signup incase we need it later
		# for fraud-style investigations.
		user_agent = self.request.headers.get( "User-Agent", "Unknown" )
		x_forwarded_for = self.request.headers.get( "X-Forwarded-For", "Unknown" )
		client_ip = self.request.remote_ip

		try:
			# Additionally since they've validated their email we'll add them to Stripe
			customer_id = yield local_tasks.stripe_create_customer(
				new_user.email,
				new_user.name,
				new_user.phone_number,
				self.json[ "stripe_token" ],
				{
					"user_agent": user_agent,
					"client_ip": client_ip,
					"x_forwarded_for": x_forwarded_for,
				}
			)
		except stripe.error.CardError as e:
			logit( "Card declined: " )
			logit( e )
			self.write({
				"success": False,
				"code": "INVALID_CARD_ERROR",
				"msg": "Invalid payment information!"
			})
			self.dbsession.rollback()
			raise gen.Return()
		except stripe.error.StripeError as e:
			logit( "Exception occurred while creating stripe account: " )
			logit( e )
			self.write({
				"success": False,
				"code": "GENERIC_STRIPE_ERROR",
				"msg": "An error occurred while communicating with the Stripe API."
			})
			self.dbsession.rollback()
			raise gen.Return()
		except Exception as e:
			logit( "Exception occurred while creating stripe account: " )
			logit( e )
			self.write({
				"success": False,
				"code": "UNKNOWN_ERROR",
				"msg": "Some unknown error occurred, this shouldn't happen!"
			})
			self.dbsession.rollback()
			raise gen.Return()

		# Set user's payment_id to the Stripe customer ID
		new_user.payment_id = customer_id
		
		self.dbsession.commit()
		
		# Add default projects to the user's account
		for default_project_data in DEFAULT_PROJECT_ARRAY:
			project_name = default_project_data[ "name" ]
			
			logit( "Adding default project name '" + project_name + "' to the user's account..." )
			
			new_project = Project()
			new_project.name = project_name
			
			# Add the user to the project so they can access it
			new_project.users.append(
				new_user
			)
			
			new_project_version = ProjectVersion()
			new_project_version.version = 1
			new_project_version.project_json = json.dumps(
				default_project_data
			)
			
			# Add new version to the project
			new_project.versions.append(
				new_project_version
			)
			
			new_project_config = ProjectConfig()
			new_project_config.project_id = new_project.id
			new_project_config.config_json = json.dumps(
				DEFAULT_PROJECT_CONFIG
			)
		
			# Add project config to the new project
			new_project.configs.append(
				new_project_config
			)
			
			self.dbsession.add( new_project )
			
		self.dbsession.commit()
		
		# Send registration confirmation link to user's email address
		# The first time they authenticate via this link it will both confirm
		# their email address and authenticate them.
		logit( "Sending user their registration confirmation email..." )
		yield local_tasks.send_registration_confirmation_email(
			self.json[ "email" ],
			raw_email_authentication_token
		)

		self.write({
			"success": True,
			"result": {
				"msg": "Registration was successful! Please check your inbox to validate your email address and to log in."
			}
		})
		
		# This is sent internally so that we can keep tabs on new users coming through.
		local_tasks.send_internal_registration_confirmation_email(
			self.json[ "email" ],
			self.json[ "name" ],
			self.json[ "phone" ]
		)
		
class EmailLinkAuthentication( BaseHandler ):
	@gen.coroutine
	def get( self, email_authentication_token=None ):
		"""
		This is the endpoint which is linked to in the email send out to the user.
		
		Currently this responds with ugly text errors, but eventually it will be just
		another REST-API endpoint.
		"""
		logit( "User is authenticating via email link" )
		
		# Query for the provided authentication token
		email_authentication_token = self.dbsession.query( EmailAuthToken ).filter_by(
			token=str( email_authentication_token )
		).first()
		
		if email_authentication_token == None:
			logit( "User's token was not found in the database" )
			self.write( "Invalid authentication token, did you copy the link correctly?" )
			raise gen.Return()
			
		# Calculate token age
		token_age = ( int( time.time() ) - email_authentication_token.timestamp )
		
		# Check if the token is expired
		if email_authentication_token.is_expired == True:
			logit( "The user's email token was already marked as expired." )
			self.write( "That email token has expired, please try authenticating again to request a new one." )
			raise gen.Return()
		
		# Check if the token is older than the allowed lifetime
		# If it is then mark it expired and return an error
		if token_age >= int( os.environ.get( "email_token_lifetime" ) ):
			logit( "The user's email token was too old and was marked as expired." )
			
			# Mark the token as expired in the database
			email_authentication_token.is_expired = True
			self.dbsession.commit()
			
			self.write( "That email token has expired, please try authenticating again to request a new one." )
			raise gen.Return()
		
		"""
		NOTE: We've disabled expiration of email links on click for Enrique Enciso since
		he wants to use it for his team and they want to share an account. This is basically
		a holdover until we have more proper team support.
		
		# Since the user has now authenticated
		# Mark the token as expired in the database
		email_authentication_token.is_expired = True
		"""
		
		# Pull the user's organization
		user_organization = self.dbsession.query( Organization ).filter_by(
			id=email_authentication_token.user.organization_id
		).first()
		
		# Check if the user has previously authenticated via
		# their email address. If not we'll mark their email
		# as validated as well.
		if email_authentication_token.user.email_verified == False:
			email_authentication_token.user.email_verified = True
			
			# Check if there are reserved AWS accounts available
			aws_reserved_account = self.dbsession.query( AWSAccount ).filter_by(
				aws_account_status="AVAILABLE"
			).first()
			
			# If one exists, add it to the account
			if aws_reserved_account != None:
				logit( "Adding a reserved AWS account to the newly registered Refinery account..." )
				aws_reserved_account.aws_account_status = "IN_USE"
				aws_reserved_account.organization_id = user_organization.id
				self.dbsession.commit()
				
				# Don't yield because we don't care about the result
				# Unfreeze/thaw the account so that it's ready for the new user
				# This takes ~30 seconds - worth noting. But that **should** be fine.
				local_tasks.unfreeze_aws_account(
					aws_reserved_account.to_dict()
				)
		
		self.dbsession.commit()
		
		# Check if the user's account is disabled
		# If it's disabled don't allow the user to log in at all.
		if email_authentication_token.user.disabled == True:
			logit( "User login was denied due to their account being disabled!" )
			self.write( "Your account is currently disabled, please contact customer support for more information." )
			raise gen.Return()
		
		# Check if the user's organization is disabled
		# If it's disabled don't allow the user to log in at all.
		if user_organization.disabled == True:
			logit( "User login was denied due to their organization being disabled!" )
			self.write( "Your organization is currently disabled, please contact customer support for more information." )
			raise gen.Return()
		
		logit( "User authenticated successfully" )
		
		# Authenticate the user via secure cookie
		self.authenticate_user_id(
			email_authentication_token.user.id
		)
		
		self.redirect(
			"/"
		)
	
class GetAuthenticationStatus( BaseHandler ):
	@authenticated
	@gen.coroutine
	def get( self ):
		current_user = self.get_authenticated_user()

		if current_user:
			intercom_user_hmac = hmac.new(
				# secret key (keep safe!)
				os.environ["intercom_hmac_secret"],
				# user's email address
				current_user.email,
				# hash function
				digestmod=hashlib.sha256
			).hexdigest()

			self.write({
				"authenticated": True,
				"name": current_user.name,
				"email": current_user.email,
				"permission_level": current_user.permission_level,
				"trial_information": get_user_free_trial_information(
					self.get_authenticated_user()
				),
				"intercom_user_hmac": intercom_user_hmac
			})
			return

		self.write({
			"success": True,
			"authenticated": False
		})

class Authenticate( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		This fires off an authentication email for a given user.
		"""
		schema = {
			"type": "object",
			"properties": {
				"email": {
					"type": "string",
				}
			},
			"required": [
				"email"
			]
		}
		
		validate_schema( self.json, schema )
		
		# Get user based off of the provided email
		user = self.dbsession.query( User ).filter_by(
			email=self.json[ "email" ]
		).first()
		
		if user == None:
			self.write({
				"success": False,
				"code": "USER_NOT_FOUND",
				"msg": "No user was found with that email address."
			})
			raise gen.Return()
		
		# Generate an auth token and add it to the user's account
		# Create a new email auth token as well
		email_auth_token = EmailAuthToken()
		
		# Pull out the authentication token
		raw_email_authentication_token = email_auth_token.token

		# Add the token to the list of the user's token
		user.email_auth_tokens.append(
			email_auth_token
		)
		
		self.dbsession.commit()
		
		yield local_tasks.send_authentication_email(
			user.email,
			raw_email_authentication_token
		)
		
		self.write({
			"success": True,
			"msg": "Sent an authentication email to the user. Please click the link in the email to log in to Refinery!"
		})

class Logout( BaseHandler ):
	@gen.coroutine
	def post( self ):
		self.clear_cookie( "session" )
		self.write({
			"success": True
		})
		
class GetBillingMonthTotals( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Pulls the billing totals for a given date range.
		
		This allows for the frontend to pull things like:
		* The user's current total costs for the month
		* The total costs for the last three months.
		"""
		schema = {
			"type": "object",
			"properties": {
				"billing_month": {
					"type": "string",
					"pattern": "^\d\d\d\d\-\d\d$",
				}
			},
			"required": [
				"billing_month"
			]
		}
		
		validate_schema( self.json, schema )

		credentials = self.get_authenticated_user_cloud_configuration()
		
		billing_data = yield local_tasks.get_sub_account_month_billing_data(
			credentials[ "account_id" ],
			credentials[ "account_type" ],
			self.json[ "billing_month" ],
			True
		)
		
		self.write({
			"success": True,
			"billing_data": billing_data,
		})
		
def get_last_month_start_and_end_date_strings():
	"""
	Returns the start date string of the previous month and
	the start date of the current month for pulling AWS
	billing for the last month.
	"""
	# Get first day of last month
	today_date = datetime.date.today()
	one_month_ago_date = datetime.date.today() - datetime.timedelta( days=30 )
		
	return {
		"current_date": today_date.strftime( "%Y-%m-%d" ),
		"month_start_date": one_month_ago_date.strftime( "%Y-%m-01" ),
		"next_month_first_day": today_date.strftime( "%Y-%m-01" ),
	}
		
def get_current_month_start_and_end_date_strings():
	"""
	Returns the start date string of this month and
	the start date of the next month for pulling AWS
	billing for the current month.
	"""
	# Get tomorrow date
	today_date = datetime.date.today()
	tomorrow_date = datetime.date.today() + datetime.timedelta( days=1 )
	start_date = tomorrow_date
	
	# We could potentially be on the last day of the month
	# making tomorrow the next month! Check for this case.
	# If it's the case then we'll just set the start date to today
	if tomorrow_date.month == today_date.month:
		start_date = today_date
	
	# Get first day of next month
	current_month_num = today_date.month
	current_year_num = today_date.year
	next_month_num = current_month_num + 1
	
	# Check if we're on the last month
	# If so the next month number is 1
	# and we should add 1 to the year
	if current_month_num == 12:
		next_month_num = 1
		current_year_num = current_year_num + 1
		
	next_month_start_date = datetime.date(
		current_year_num,
		next_month_num,
		1
	)
		
	return {
		"current_date": tomorrow_date.strftime( "%Y-%m-%d" ),
		"month_start_date": tomorrow_date.strftime( "%Y-%m-01" ),
		"next_month_first_day": next_month_start_date.strftime( "%Y-%m-%d" ),
	}
		
class GetBillingDateRangeForecast( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Pulls the billing totals for a given date range.
		
		This allows for the frontend to pull things like:
		* The user's current total costs for the month
		* The total costs for the last three months.
		"""
		current_user = self.get_authenticated_user()
		credentials = self.get_authenticated_user_cloud_configuration()
		
		date_info = get_current_month_start_and_end_date_strings()
		
		forecast_data = yield local_tasks.get_sub_account_billing_forecast(
			credentials[ "account_id" ],
			date_info[ "current_date"],
			date_info[ "next_month_first_day" ],
			"monthly"
		)
		
		self.write( forecast_data )

class RunBillingWatchdogJob( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		This job checks the running account totals of each AWS account to see
		if their usage has gone over the safety limits. This is mainly for free
		trial users and for alerting users that they may incur a large bill.
		"""
		self.write({
			"success": True,
			"msg": "Watchdog job has been started!"
		})
		self.finish()
		logit( "[ STATUS ] Initiating billing watchdog job, scanning all accounts to check for billing anomalies..." )
		aws_account_running_cost_list = yield local_tasks.pull_current_month_running_account_totals()
		logit( "[ STATUS ] " + str( len( aws_account_running_cost_list ) ) + " account(s) pulled from billing, checking against rules..." )
		yield local_tasks.enforce_account_limits( aws_account_running_cost_list )
		
def is_organization_first_month( aws_account_id ):
	# Pull the relevant organization from the database to check
	# how old the account is to know if the first-month's base fee should be applied.
	dbsession = DBSession()
	aws_account = dbsession.query( AWSAccount ).filter_by(
		account_id=aws_account_id
	).first()
	organization = dbsession.query( Organization ).filter_by(
		id=aws_account.organization_id
	).first()
	organization_dict = organization.to_dict()
	dbsession.close()
	
	account_creation_dt = datetime.datetime.fromtimestamp(
		organization.timestamp
	)
	
	current_datetime = datetime.datetime.now()
	
	if account_creation_dt > ( current_datetime - datetime.timedelta( days=40 ) ):
		return True
	
	return False
		
class RunMonthlyStripeBillingJob( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		Runs at the first of the month and creates auto-finalizing draft
		invoices for all Refinery customers. After it does this it emails
		the "billing_alert_email" email with a notice to review the drafts
		before they auto-finalize after one-hour.
		"""
		self.write({
			"success": True,
			"msg": "The billing job has been started!"
		})
		self.finish()
		logit( "[ STATUS ] Running monthly Stripe billing job to invoice all Refinery customers." )
		date_info = get_last_month_start_and_end_date_strings()
		
		logit( "[ STATUS ] Generating invoices for " + date_info[ "month_start_date" ] + " -> " + date_info[ "next_month_first_day" ]  )
		
		yield local_tasks.generate_managed_accounts_invoices(
			date_info[ "month_start_date"],
			date_info[ "next_month_first_day" ],
		)
		logit( "[ STATUS ] Stripe billing job has completed!" )
		
class HealthHandler( BaseHandler ):
	def get( self ):
		# Just run a dummy database query to ensure it's working
		self.dbsession.query( User ).first()
		self.write({
			"success": True,
			"status": "ok"
		})
		
class AddCreditCardToken( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Adds a credit card token to a given user's Stripe record.
		
		THIS DOES NOT STORE CREDIT CARD INFORMATION, DO NOT EVER PASS
		CREDIT CARD INFORMATION TO IT. DON'T EVEN *THINK* ABOUT DOING
		IT OR I WILL PERSONALLY SLAP YOU. -mandatory
		"""
		schema = {
			"type": "object",
			"properties": {
				"token": {
					"type": "string"
				}
			},
			"required": [
				"token"
			]
		}
		
		validate_schema( self.json, schema )
		
		current_user = self.get_authenticated_user()
		
		yield local_tasks.associate_card_token_with_customer_account(
			current_user.payment_id,
			self.json[ "token" ]
		)
		
		self.write({
			"success": True,
			"msg": "The credit card has been successfully added to your account!"
		})
		
class ListCreditCards( BaseHandler ):
	@authenticated
	@gen.coroutine
	def get( self ):
		"""
		List the credit cards the user has on file, returns
		just the non-PII info that we get back from Stripe
		"""
		current_user = self.get_authenticated_user()
		
		cards_info_list = yield local_tasks.get_account_cards(
			current_user.payment_id,
		)
		
		# Filter card info
		filtered_card_info_list = []
		
		# The keys we're fine with passing from back Stripe
		returnable_keys = [
			"id",
			"brand",
			"country",
			"exp_month",
			"exp_year",
			"last4",
			"is_primary"
		]
		
		for card_info in cards_info_list:
			filtered_card_info = {}
			for key, value in card_info.iteritems():
				if key in returnable_keys:
					filtered_card_info[ key ] = value
			
			filtered_card_info_list.append(
				filtered_card_info
			)
		
		self.write({
			"success": True,
			"cards": filtered_card_info_list
		})
		
class DeleteCreditCard( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Deletes a credit card from the user's Stripe account.
		
		This is not allowed if the payment method is the only
		one on file for that account.
		"""
		schema = {
			"type": "object",
			"properties": {
				"id": {
					"type": "string"
				}
			},
			"required": [
				"id"
			]
		}
		
		validate_schema( self.json, schema )
		
		current_user = self.get_authenticated_user()
		
		try:
			yield local_tasks.delete_card_from_account(
				current_user.payment_id,
				self.json[ "id" ]
			)
		except CardIsPrimaryException:
			self.error(
				"You cannot delete your primary payment method, you must have at least one available to pay your bills.",
				"CANT_DELETE_PRIMARY"
			)
			raise gen.Return()
		
		self.write({
			"success": True,
			"msg": "The card has been successfully been deleted from your account!"
		})
		
class MakeCreditCardPrimary( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Sets a given card to be the user's primary credit card.
		"""
		schema = {
			"type": "object",
			"properties": {
				"id": {
					"type": "string"
				}
			},
			"required": [
				"id"
			]
		}
		
		validate_schema( self.json, schema )
		
		current_user = self.get_authenticated_user()
		
		try:
			yield local_tasks.set_stripe_customer_default_payment_source(
				current_user.payment_id,
				self.json[ "id" ]
			)
		except:
			self.error(
				"An error occurred while making the card your primary.",
				"GENERIC_MAKE_PRIMARY_ERROR"
			)
		
		self.write({
			"success": True,
			"msg": "You have set this card to be your primary succesfully."
		})
		
def get_user_free_trial_information( input_user ):
	return_data = {
		"trial_end_timestamp": 0,
		"trial_started_timestamp": 0,
		"trial_over": False,
		"is_using_trial": True,
	}
	
	# If the user has a payment method on file they can't be using the
	# free trial.
	if input_user.has_valid_payment_method_on_file == True:
		return_data[ "is_using_trial" ] = False
		return_data[ "trial_over" ] = True
		
	# Calculate when the trial is over
	trial_length_in_seconds = ( 60 * 60 * 24 * 14 )
	return_data[ "trial_started_timestamp" ] = input_user.timestamp
	return_data[ "trial_end_timestamp" ] = input_user.timestamp + trial_length_in_seconds
	
	# Calculate if the user is past their free trial
	current_timestamp = int( time.time() )
	
	# Calculate time since user sign up
	seconds_since_signup = current_timestamp - input_user.timestamp
	
	# If it's been over 14 days since signup the user
	# has exhausted their free trial
	if seconds_since_signup > trial_length_in_seconds:
		return_data[ "trial_over" ] = True
		
	return return_data
	
@gen.coroutine
def is_build_package_cached( credentials, language, libraries ):
	# If it's an empty list just return True
	if len( libraries ) == 0:
		raise gen.Return( True )
	
	# TODO just accept a dict/object in of an
	# array followed by converting it to one.
	libraries_dict = {}
	for library in libraries:
		libraries_dict[ str( library ) ] = "latest"
	
	# Get the final S3 path
	final_s3_package_zip_path = yield local_tasks.get_final_zip_package_path(
		language,
		libraries_dict,
	)
	
	# Get if the package is already cached
	is_already_cached = yield local_tasks.s3_object_exists(
		credentials,
		credentials[ "lambda_packages_bucket" ],
		final_s3_package_zip_path
	)
	
	raise gen.Return( is_already_cached )
	
class CheckIfLibrariesCached( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Just returns if a given language + libraries has
		already been built and cached in S3.
		"""
		schema = {
			"type": "object",
			"properties": {
				"libraries": {
					"type": "array"
				},
				"language": {
					"type": "string",
					"enum": LAMBDA_SUPPORTED_LANGUAGES
				}
			},
			"required": [
				"libraries",
				"language"
			]
		}
		
		validate_schema( self.json, schema )
		
		credentials = self.get_authenticated_user_cloud_configuration()
		
		is_already_cached = yield is_build_package_cached(
			credentials,
			self.json[ "language" ],
			self.json[ "libraries" ]
		)
		
		self.write({
			"success": True,
			"is_already_cached": is_already_cached,
		})
	
class BuildLibrariesPackage( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Kick off a codebuild for listed build libraries.
		"""
		schema = {
			"type": "object",
			"properties": {
				"libraries": {
					"type": "array"
				},
				"language": {
					"type": "string",
					"enum": LAMBDA_SUPPORTED_LANGUAGES
				}
			},
			"required": [
				"libraries",
				"language"
			]
		}
		
		validate_schema( self.json, schema )
		
		current_user = self.get_authenticated_user()
		credentials = self.get_authenticated_user_cloud_configuration()
		
		# TODO just accept a dict/object in of an
		# array followed by converting it to one.
		libraries_dict = {}
		for library in self.json[ "libraries" ]:
			libraries_dict[ str( library ) ] = "latest"
		
		build_id = False
		
		# Get the final S3 path
		final_s3_package_zip_path = yield local_tasks.get_final_zip_package_path(
			self.json[ "language" ],
			libraries_dict,
		)
		
		if self.json[ "language" ] == "python2.7":
			build_id = yield local_tasks.start_python27_codebuild(
				credentials,
				libraries_dict
			)
		elif self.json[ "language" ] == "python3.6":
			build_id = yield local_tasks.start_python36_codebuild(
				credentials,
				libraries_dict
			)
		elif self.json[ "language" ] == "nodejs8.10":
			build_id = yield local_tasks.start_node810_codebuild(
				credentials,
				libraries_dict
			)
		elif self.json[ "language" ] == "nodejs10.16.3":
			build_id = yield local_tasks.start_node10163_codebuild(
				credentials,
				libraries_dict
			)
		elif self.json[ "language" ] == "php7.3":
			build_id = yield local_tasks.start_php73_codebuild(
				credentials,
				libraries_dict
			)
		elif self.json[ "language" ] == "ruby2.6.4":
			build_id = yield local_tasks.start_ruby264_codebuild(
				credentials,
				libraries_dict
			)
		else:
			self.error(
				"You've provided a language that Refinery does not currently support!",
				"UNSUPPORTED_LANGUAGE"
			)
			raise gen.Return()
		
		# Don't yield here because we don't care about the outcome of this task
		# we just want to kick it off in the background
		local_tasks.finalize_codebuild(
			credentials,
			build_id,
			final_s3_package_zip_path
		)
		
		self.write({
			"success": True,
		})

class GetAWSConsoleCredentials( BaseHandler ):
	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def get( self ):
		"""
		Pull the AWS credentials for the customer to log into the console.
		This is important early on so that they can still get all the serverless
		advantages that we haven't abstracted upon (and to use Cloudwatch, etc).
		"""
		credentials = self.get_authenticated_user_cloud_configuration()
		
		aws_console_signin_url = "https://" + credentials[ "account_id" ] + ".signin.aws.amazon.com/console/?region=" + os.environ.get( "region_name" )
		
		self.write({
			"success": True,
			"console_credentials": {
				"username": credentials[ "iam_admin_username" ],
				"password": credentials[ "iam_admin_password" ],
				"signin_url": aws_console_signin_url,
			}
		})
		
		
class MaintainAWSAccountReserves( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		This job checks the number of AWS accounts in the reserve pool and will
		automatically create accounts for the pool if there are less than the
		target amount. This job is run regularly (every minute) to ensure that
		we always have enough AWS accounts ready to use.
		"""
		self.write({
			"success": True,
			"msg": "AWS account maintenance job has been kicked off!"
		})
		self.finish()
		
		dbsession = DBSession()
		
		reserved_aws_pool_target_amount = int( os.environ.get( "reserved_aws_pool_target_amount" ) )
		
		# Get the number of AWS accounts which are ready to be
		# assigned to new users that are signing up ("AVAILABLE").
		available_accounts_count = dbsession.query( AWSAccount ).filter_by(
			aws_account_status="AVAILABLE"
		).count()
		
		# Get the number of AWS accounts which have been created
		# but are not yet provision via Terraform ("CREATED").
		created_accounts_count = dbsession.query( AWSAccount ).filter_by(
			aws_account_status="CREATED"
		).count()
		
		# Get the number of AWS accounts that need to be provision
		# via Terraform on this iteration
		# At a MINIMUM we have to wait 60 seconds from the time of account creation
		# to actually perform the Terraform step.
		# We'll do 20 because it usually takes 15 to get the "Account Verified" email.
		minimum_account_age_seconds = ( 60 * 5 )
		current_timestamp = int( time.time() )
		non_setup_aws_accounts = dbsession.query( AWSAccount ).filter(
			AWSAccount.aws_account_status == "CREATED",
			AWSAccount.timestamp <= ( current_timestamp - minimum_account_age_seconds )
		).all()
		non_setup_aws_accounts_count = len( non_setup_aws_accounts )
		
		# Pull the list of AWS account IDs to work on.
		aws_account_ids = []
		for non_setup_aws_account in non_setup_aws_accounts:
			aws_account_ids.append(
				non_setup_aws_account.account_id
			)
			
		dbsession.close()
		
		# Calculate the number of accounts that have been created but not provisioned
		# That way we know how many, if any, that we need to create.
		accounts_to_create = ( reserved_aws_pool_target_amount - available_accounts_count - created_accounts_count )
		if accounts_to_create < 0:
			accounts_to_create = 0
		
		logit( "--- AWS Account Stats ---" )
		logit( "Ready for customer use: " + str( available_accounts_count ) )
		logit( "Ready for terraform provisioning: " + str( non_setup_aws_accounts_count ) )
		logit( "Not ready for initial terraform provisioning: " + str( ( created_accounts_count - non_setup_aws_accounts_count ) ) )
		logit( "Target pool amount: " + str( reserved_aws_pool_target_amount ) )
		logit( "Number of accounts to be created: " + str( accounts_to_create ) )
		
		# Kick off the terraform apply jobs for the accounts which are "aged" for it.
		for aws_account_id in aws_account_ids:
			dbsession = DBSession()
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == aws_account_id,
			).first()
			current_aws_account_dict = current_aws_account.to_dict()
			dbsession.close()
			
			logit( "Kicking off terraform set-up for AWS account '" + current_aws_account_dict[ "account_id" ] + "'..." )
			try:
				account_provisioning_details = yield local_tasks.terraform_configure_aws_account(
					current_aws_account_dict
				)
				
				logit( "Adding AWS account to the database the pool of \"AVAILABLE\" accounts..." )
				
				dbsession = DBSession()
				current_aws_account = dbsession.query( AWSAccount ).filter(
					AWSAccount.account_id == aws_account_id,
				).first()
				
				# Update the AWS account with this new information
				current_aws_account.redis_hostname = account_provisioning_details[ "redis_hostname" ]
				current_aws_account.terraform_state = account_provisioning_details[ "terraform_state" ]
				current_aws_account.ssh_public_key = account_provisioning_details[ "ssh_public_key" ]
				current_aws_account.ssh_private_key = account_provisioning_details[ "ssh_private_key" ]
				current_aws_account.aws_account_status = "AVAILABLE"
				
				# Create a new terraform state version
				terraform_state_version = TerraformStateVersion()
				terraform_state_version.terraform_state = account_provisioning_details[ "terraform_state" ]
				current_aws_account.terraform_state_versions.append(
					terraform_state_version
				)
			except Exception as e:
				logit( "An error occurred while provision AWS account '" + current_aws_account.account_id + "' with terraform!", "error" )
				logit( e )
				logit( "Marking the account as 'CORRUPT'..." )
				
				# Mark the account as corrupt since the provisioning failed.
				current_aws_account.aws_account_status = "CORRUPT"
			
			logit( "Commiting new account state of '" + current_aws_account.aws_account_status + "' to database..." )
			dbsession.add(current_aws_account)
			dbsession.commit()
			
			logit( "Freezing the account until it's used by someone..." )
			
			TaskSpawner._freeze_aws_account(
				current_aws_account.to_dict()
			)
			
			logit( "Account frozen successfully." )
			
		# Create sub-accounts and let them age before applying terraform
		for i in range( 0, accounts_to_create ):
			logit( "Creating a new AWS sub-account for later terraform use..." )
			# We have to yield because you can't mint more than one sub-account at a time
			# (AWS can litterally only process one request at a time).
			try:
				yield local_tasks.create_new_sub_aws_account(
					"MANAGED",
					False
				)
			except:
				logit( "An error occurred while creating an AWS sub-account.", "error" )
				pass
		
		dbsession.close()
			
class PerformTerraformUpdateOnFleet( BaseHandler ):
	@gen.coroutine
	def get( self ):
		self.write({
			"success": True,
			"msg": "Terraform apply job has been kicked off, I hope you planned first!"
		})
		self.finish()
		
		dbsession = DBSession()
		
		aws_accounts = dbsession.query( AWSAccount ).filter(
			sql_or(
				AWSAccount.aws_account_status == "IN_USE",
				AWSAccount.aws_account_status == "AVAILABLE",
			)
		).all()
		
		final_email_html = """
		<h1>Terraform Apply Results Across the Customer Fleet</h1>
		If the subject line doesn't read <b>APPLY SUCCEEDED</b> you have some work to do!
		"""
		
		issue_occurred_during_updates = False
		
		# Pull the list of AWS account IDs to work on.
		aws_account_ids = []
		for aws_account in aws_accounts:
			aws_account_ids.append(
				aws_account.account_id
			)
			
		dbsession.close()
		
		for aws_account_id in aws_account_ids:
			dbsession = DBSession()
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == aws_account_id,
			).first()
			current_aws_account_dict = current_aws_account.to_dict()
			dbsession.close()
			
			logit( "Running 'terraform apply' against AWS Account " + current_aws_account_dict[ "account_id" ] )
			terraform_apply_results = yield local_tasks.terraform_apply(
				current_aws_account_dict
			)
			
			# Write the old terraform version to the database
			logit( "Updating current tfstate for the AWS account..." )
			
			dbsession = DBSession()
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == aws_account_id,
			).first()
			
			previous_terraform_state = TerraformStateVersion()
			previous_terraform_state.aws_account_id = current_aws_account.id
			previous_terraform_state.terraform_state = terraform_apply_results[ "original_tfstate" ]
			current_aws_account.terraform_state_versions.append(
				previous_terraform_state
			)
			
			# Update the current terraform state as well.
			current_aws_account.terraform_state = terraform_apply_results[ "new_tfstate" ]
			
			dbsession.add( current_aws_account )
			dbsession.commit()
			dbsession.close()
			
			# Convert terraform plan terminal output to HTML
			ansiconverter = Ansi2HTMLConverter()
			
			if terraform_apply_results[ "success" ]:
				terraform_output_html = ansiconverter.convert(
					terraform_apply_results[ "stdout" ]
				)
			else:
				terraform_output_html = ansiconverter.convert(
					terraform_apply_results[ "stderr" ]
				)
				issue_occurred_during_updates = True
				
			final_email_html += "<hr /><h1>AWS Account " + current_aws_account_dict[ "account_id" ] + "</h1>"
			final_email_html += terraform_output_html
			
		final_email_html += "<hr /><b>That is all.</b>"
		
		logit( "Sending email with results from 'terraform apply'..." )
		
		final_email_subject = "Terraform Apply Results from Across the Fleet " + str( int( time.time() ) ) # Make subject unique so Gmail doesn't group
		if issue_occurred_during_updates:
			final_email_subject = "[ APPLY FAILED ] " + final_email_subject
		else:
			final_email_subject = "[ APPLY SUCCEEDED ] " + final_email_subject
		
		yield local_tasks.send_email(
			os.environ.get( "alerts_email" ),
			final_email_subject,
			False, # No text version of email
			final_email_html
		)
		
		dbsession.close()
			
class PerformTerraformPlanOnFleet( BaseHandler ):
	@gen.coroutine
	def get( self ):
		self.write({
			"success": True,
			"msg": "Terraform plan job has been kicked off!"
		})
		self.finish()
		
		dbsession = DBSession()
		
		aws_accounts = dbsession.query( AWSAccount ).filter(
			sql_or(
				AWSAccount.aws_account_status == "IN_USE",
				AWSAccount.aws_account_status == "AVAILABLE",
			)
		).all()
		
		final_email_html = """
		<h1>Terraform Plan Results Across the Customer Fleet</h1>
		Please note that this is <b>not</b> applying these changes.
		It is purely to understand what would happen if we did.
		"""
		
		total_accounts = len( aws_accounts )
		counter = 1
		
		# Pull the list of AWS account IDs to work on.
		aws_account_ids = []
		for aws_account in aws_accounts:
			aws_account_ids.append(
				aws_account.account_id
			)
			
		dbsession.close()
		
		for aws_account_id in aws_account_ids:
			dbsession = DBSession()
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == aws_account_id,
			).first()
			current_aws_account = current_aws_account.to_dict()
			dbsession.close()
			
			logit( "Performing a terraform plan for AWS account " + str( counter ) + "/" + str( total_accounts ) + "..." )
			terraform_plan_output = yield local_tasks.terraform_plan(
				current_aws_account
			)
			
			# Convert terraform plan terminal output to HTML
			ansiconverter = Ansi2HTMLConverter()
			terraform_output_html = ansiconverter.convert(
				terraform_plan_output
			)
			
			final_email_html += "<hr /><h1>AWS Account " + current_aws_account[ "account_id" ] + "</h1>"
			final_email_html += terraform_output_html
			counter = counter + 1
			
		final_email_html += "<hr /><b>That is all.</b>"
		
		logit( "Sending email with results from terraform plan..." )
		yield local_tasks.send_email(
			os.environ.get( "alerts_email" ),
			"Terraform Plan Results from Across the Fleet " + str( int( time.time() ) ), # Make subject unique so Gmail doesn't group
			False, # No text version of email
			final_email_html
		)
			
class StashStateLog( BaseHandler ):
	def post( self ):
		"""
		For storing state logs that the frontend sends
		to the backend to later be used for replaying sessions, etc.
		"""
		schema = {
			"type": "object",
			"properties": {
				"session_id": {
					"type": "string"
				},
				"state": {
					"type": "object",
				}
			},
			"required": [
				"session_id",
				"state"
			]
		}
		
		validate_schema( self.json, schema )
		
		authenticated_user_id = self.get_authenticated_user_id()
		
		state_log = StateLog()
		state_log.session_id = self.json[ "session_id" ]
		state_log.state = self.json[ "state" ]
		state_log.user_id = authenticated_user_id
		
		self.dbsession.add( state_log )
		self.dbsession.commit()
		
		self.write({
			"success": True,
		})
		
class AdministrativeAssumeAccount( BaseHandler ):
	def get( self, user_id=None ):
		"""
		For helping customers with their accounts.
		"""
		if not user_id:
			self.write({
				"success": False,
				"msg": "You must specify a user_id via the URL (/UUID/)."
			})
		
		# Authenticate the user via secure cookie
		self.authenticate_user_id(
			user_id
		)
		
		self.redirect(
			"/"
		)
		
class UpdateIAMConsoleUserIAM( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		This blows away all the IAM policies for all customer AWS accounts
		and updates it with the latest policy.
		"""
		self.write({
			"success": True,
			"msg": "Console accounts are being updated!"
		})
		self.finish()
		
		dbsession = DBSession()
		aws_accounts = dbsession.query( AWSAccount ).filter(
			sql_or(
				AWSAccount.aws_account_status == "IN_USE",
				AWSAccount.aws_account_status == "AVAILABLE",
			)
		).all()
		
		aws_account_dicts = []
		for aws_account in aws_accounts:
			aws_account_dicts.append(
				aws_account.to_dict()
			)
		dbsession.close()
		
		for aws_account_dict in aws_account_dicts:
			logit( "Updating console account for AWS account ID " + aws_account_dict[ "account_id" ] + "...")
			yield local_tasks.recreate_aws_console_account(
				aws_account_dict,
				False
			)
		
		logit( "AWS console accounts updated successfully!" )
		
class OnboardThirdPartyAWSAccountPlan( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		Imports a third-party AWS account into the database and sends out
		a terraform plan email with what will happen when it's fully set up.
		"""
		
		# Get AWS account ID
		account_id = self.get_argument(
			"account_id",
			default=None,
			strip=True
		)
		
		if not account_id:
			self.write({
				"success": False,
				"msg": "Please provide an 'account_id' to onboard this AWS account!"
			})
			raise gen.Return()
			
		final_email_html = """
		<h1>Terraform Plan Results for Onboarding Third-Party Customer AWS Account</h1>
		Please note that this is <b>not</b> applying these changes.
		It is purely to understand what would happen if we did.
		"""
			
		# First we set up the AWS Account in our database so we have a record
		# of it going forward. This also creates the AWS console user.
		logit( "Adding third-party AWS account to the database..." )
		yield local_tasks.create_new_sub_aws_account(
			"THIRDPARTY",
			account_id
		)
		
		dbsession = DBSession()
		third_party_aws_account = dbsession.query( AWSAccount ).filter_by(
			account_id=account_id,
			account_type="THIRDPARTY"
		).first()
		third_party_aws_account_dict = third_party_aws_account.to_dict()
		dbsession.close()
		
		logit( "Performing a terraform plan against the third-party account..." )
		terraform_plan_output = yield local_tasks.terraform_plan(
			third_party_aws_account_dict
		)
		
		# Convert terraform plan terminal output to HTML
		ansiconverter = Ansi2HTMLConverter()
		terraform_output_html = ansiconverter.convert(
			terraform_plan_output
		)
		
		final_email_html += "<hr /><h1>AWS Account " + third_party_aws_account_dict[ "account_id" ] + "</h1>"
		final_email_html += terraform_output_html
			
		final_email_html += "<hr /><b>That is all.</b>"
		
		logit( "Sending email with results from terraform plan..." )
		yield local_tasks.send_email(
			os.environ.get( "alerts_email" ),
			"Terraform Plan Results for Onboarding Third-Party AWS Account " + str( int( time.time() ) ), # Make subject unique so Gmail doesn't group
			False, # No text version of email
			final_email_html
		)
		
		self.write({
			"success": True,
			"msg": "Successfully added AWS account " + account_id + " to database and sent plan email!"
		})
		
class OnboardThirdPartyAWSAccountApply( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		Finalizes the third-party AWS account onboarding import process.
		
		This should only be done after the Terraform plan has been reviewed
		and it looks appropriate to be applied.
		"""
		
		# Get AWS account ID
		account_id = self.get_argument(
			"account_id",
			default=None,
			strip=True
		)
		
		# Get Refinery user ID
		user_id = self.get_argument(
			"user_id",
			default=None,
			strip=True
		)
		
		if not account_id:
			self.write({
				"success": False,
				"msg": "Please provide an 'account_id' to onboard this AWS account!"
			})
			raise gen.Return()
			
		if not user_id:
			self.write({
				"success": False,
				"msg": "Please provide an 'user_id' to onboard this AWS account!"
			})
			raise gen.Return()
			
		dbsession = DBSession()
		third_party_aws_account = dbsession.query( AWSAccount ).filter_by(
			account_id=account_id,
			account_type="THIRDPARTY"
		).first()
		third_party_aws_account_dict = third_party_aws_account.to_dict()
		dbsession.close()
		
		logit( "Creating the '" + THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME + "' role for Lambda executions..." )
		yield local_tasks.create_third_party_aws_lambda_execute_role(
			third_party_aws_account_dict
		)
			
		try:
			logit( "Creating Refinery base infrastructure on third-party AWS account..." )
			account_provisioning_details = yield local_tasks.terraform_configure_aws_account(
				third_party_aws_account_dict
			)
	
			dbsession = DBSession()
			
			# Get the AWS account specified
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == account_id,
			).first()
			
			# Pull the user from the database
			refinery_user = dbsession.query( User ).filter_by(
				id=user_id
			).first()
			
			# Grab the previous AWS account specified with the Refinery account
			previous_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.organization_id == refinery_user.organization_id
			).first()
			
			previous_aws_account_dict = previous_aws_account.to_dict()
			previous_aws_account_id = previous_aws_account.id
			
			logit( "Previously-assigned AWS Account has UUID of " + previous_aws_account_id )
			
			# Set the previously-assigned AWS account to be
			previous_aws_account.aws_account_status = "NEEDS_CLOSING"
			previous_aws_account.organization_id = None
			
			# Update the AWS account with this new information
			current_aws_account.redis_hostname = account_provisioning_details[ "redis_hostname" ]
			current_aws_account.terraform_state = account_provisioning_details[ "terraform_state" ]
			current_aws_account.ssh_public_key = account_provisioning_details[ "ssh_public_key" ]
			current_aws_account.ssh_private_key = account_provisioning_details[ "ssh_private_key" ]
			current_aws_account.aws_account_status = "IN_USE"
			current_aws_account.organization_id = refinery_user.organization_id
			
			# Create a new terraform state version
			terraform_state_version = TerraformStateVersion()
			terraform_state_version.terraform_state = account_provisioning_details[ "terraform_state" ]
			current_aws_account.terraform_state_versions.append(
				terraform_state_version
			)
		except Exception as e:
			logit( "An error occurred while provision AWS account '" + current_aws_account.account_id + "' with terraform!", "error" )
			logit( e )
			logit( "Marking the account as 'CORRUPT'..." )
			
			# Mark the account as corrupt since the provisioning failed.
			current_aws_account.aws_account_status = "CORRUPT"
			dbsession.add( current_aws_account )
			dbsession.commit()
			dbsession.close()
			
			self.write({
				"success": False,
				"exception": str( e ),
				"msg": "An error occurred while provisioning AWS account."
			})
			
			raise gen.Return()
		
		logit( "AWS account terraform apply has completed." )
		dbsession.add( previous_aws_account )
		dbsession.add( current_aws_account )
		dbsession.commit()
		dbsession.close()
		
		# Close the previous Refinery-managed AWS account
		logit( "Closing previously-assigned Refinery AWS account..." )
		logit( "Freezing the account so it costs us less while we do the process of closing it..." )
		yield local_tasks.freeze_aws_account(
			previous_aws_account_dict
		)
		
		self.write({
			"success": True,
			"msg": "Successfully added third-party AWS account " + account_id + " to user ID " + user_id + "."
		})
		
class ClearAllS3BuildPackages( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		Clears out the S3 build packages of all the Refinery users.
		
		This just forces everyone to do a rebuild the next time they run code with packages.
		"""
		self.write({
			"success": True,
			"msg": "Clear build package job kicked off successfully!"
		})
		self.finish()
		
		dbsession = DBSession()
		aws_accounts = dbsession.query( AWSAccount ).filter(
			sql_or(
				AWSAccount.aws_account_status == "IN_USE",
				AWSAccount.aws_account_status == "AVAILABLE",
			)
		).all()
		
		aws_account_dicts = []
		for aws_account in aws_accounts:
			aws_account_dicts.append(
				aws_account.to_dict()
			)
		dbsession.close()
		
		for aws_account_dict in aws_account_dicts:
			logit( "Clearing build packages for account ID " + aws_account_dict[ "account_id" ] + "..." )
			yield clear_sub_account_packages(
				aws_account_dict
			)
			
		logit( "S3 package clearing complete." )
		
@gen.coroutine
def clear_sub_account_packages( credentials ):
	while True:
		package_paths = yield local_tasks.get_build_packages(
			credentials,
			"",
			1000
		)
		
		logit( "Deleting #" + str( len( package_paths ) ) + " build packages for account ID " + credentials[ "account_id" ] + "..." )

		if len( package_paths ) == 0:
			break
		
		yield local_tasks.bulk_s3_delete(
			credentials,
			credentials[ "lambda_packages_bucket" ],
			package_paths
		)
		
class CreateProjectShortlink( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Creates a new project shortlink for a project so it can be shared
		and "forked" by other people on the platform.
		"""
		schema = {
			"type": "object",
			"properties": {
				"diagram_data": {
					"type": "object",
				}
			},
			"required": [
				"diagram_data"
			]
		}
		
		validate_schema( self.json, schema )
		
		new_project_shortlink = ProjectShortLink()
		new_project_shortlink.project_json = self.json[ "diagram_data" ]
		self.dbsession.add( new_project_shortlink )
		self.dbsession.commit()
		
		self.write({
			"success": True,
			"msg": "Project short link created successfully!",
			"result": {
				"project_short_link_id": new_project_shortlink.short_id
			}
		})
		
class GetProjectShortlink( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Returns project JSON by the project_short_link_id
		"""
		schema = {
			"type": "object",
			"properties": {
				"project_short_link_id": {
					"type": "string",
				}
			},
			"required": [
				"project_short_link_id"
			]
		}
		
		validate_schema( self.json, schema )
		
		project_short_link = self.dbsession.query( ProjectShortLink ).filter_by(
			short_id=self.json[ "project_short_link_id" ]
		).first()
		
		if not project_short_link:
			self.write({
				"success": False,
				"msg": "Project short link was not found!"
			})
			raise gen.Return()
			
		project_short_link_dict = project_short_link.to_dict()
		
		self.write({
			"success": True,
			"msg": "Project short link created successfully!",
			"result": {
				"project_short_link_id": project_short_link_dict[ "short_id" ],
				"diagram_data": project_short_link_dict[ "project_json" ],
			}
		})

def get_tornado_app_config( is_debug ):
	return {
		"debug": is_debug,
		"ngrok_enabled": os.environ.get( "ngrok_enabled" ),
		"cookie_secret": os.environ.get( "cookie_secret_value" ),
		"compress_response": True,
		"websocket_router": WebSocketRouter()
	}

def make_websocket_server( tornado_config ):
	return tornado.web.Application([
		# WebSocket callback endpoint for live debugging Lambdas
		( r"/ws/v1/lambdas/connectback", LambdaConnectBackServer, {
			"websocket_router": tornado_config[ "websocket_router" ]
		}),
	], **tornado_config)
		
def make_app( tornado_config ):
	return tornado.web.Application([
		( r"/api/v1/health", HealthHandler ),
		( r"/authentication/email/([a-z0-9]+)", EmailLinkAuthentication ),
		( r"/api/v1/auth/me", GetAuthenticationStatus ),
		( r"/api/v1/auth/register", NewRegistration ),
		( r"/api/v1/auth/login", Authenticate ),
		( r"/api/v1/auth/logout", Logout ),
		( r"/api/v1/logs/executions/get-logs", GetProjectExecutionLogObjects ),
		( r"/api/v1/logs/executions/get-contents", GetProjectExecutionLogsPage ),
		( r"/api/v1/logs/executions/get", GetProjectExecutionLogs ),
		( r"/api/v1/logs/executions", GetProjectExecutions ),
		( r"/api/v1/aws/deploy_diagram", DeployDiagram ),
		( r"/api/v1/saved_blocks/create", SavedBlocksCreate ),
		( r"/api/v1/saved_blocks/search", SavedBlockSearch ),
		( r"/api/v1/saved_blocks/status_check", SavedBlockStatusCheck ),
		( r"/api/v1/saved_blocks/delete", SavedBlockDelete ),
		( r"/api/v1/lambdas/run", RunLambda ),
		( r"/api/v1/lambdas/logs", GetCloudWatchLogsForLambda ),
		( r"/api/v1/lambdas/env_vars/update", UpdateEnvironmentVariables ),
		( r"/api/v1/lambdas/build_libraries", BuildLibrariesPackage ),
		( r"/api/v1/lambdas/libraries_cache_check", CheckIfLibrariesCached ),
		( r"/api/v1/aws/run_tmp_lambda", RunTmpLambda ),
		( r"/api/v1/aws/infra_tear_down", InfraTearDown ),
		( r"/api/v1/aws/infra_collision_check", InfraCollisionCheck ),
		( r"/api/v1/projects/config/save", SaveProjectConfig ),
		( r"/api/v1/projects/save", SaveProject ),
		( r"/api/v1/projects/search", SearchSavedProjects ),
		( r"/api/v1/projects/get", GetSavedProject ),
		( r"/api/v1/projects/delete", DeleteSavedProject ),
		( r"/api/v1/projects/rename", RenameProject ),
		( r"/api/v1/projects/config/get", GetProjectConfig ),
		( r"/api/v1/deployments/get_latest", GetLatestProjectDeployment ),
		( r"/api/v1/deployments/delete_all_in_project", DeleteDeploymentsInProject ),
		( r"/api/v1/billing/get_month_totals", GetBillingMonthTotals ),
		( r"/api/v1/billing/creditcards/add", AddCreditCardToken ),
		( r"/api/v1/billing/creditcards/list", ListCreditCards ),
		( r"/api/v1/billing/creditcards/delete", DeleteCreditCard ),
		( r"/api/v1/billing/creditcards/make_primary", MakeCreditCardPrimary ),
		( r"/api/v1/iam/console_credentials", GetAWSConsoleCredentials ),
		( r"/api/v1/internal/log", StashStateLog ),
		( r"/api/v1/project_short_link/create", CreateProjectShortlink ),
		( r"/api/v1/project_short_link/get", GetProjectShortlink ),
		# WebSocket endpoint for live debugging Lambdas
		( r"/ws/v1/lambdas/livedebug", ExecutionsControllerServer, {
			"websocket_router": tornado_config[ "websocket_router" ]
		}),
		
		# Temporarily disabled since it doesn't cache the CostExplorer results
		#( r"/api/v1/billing/forecast_for_date_range", GetBillingDateRangeForecast ),
		
		# These are "services" which are only called by external crons, etc.
		# External users are blocked from ever reaching these routes
		( r"/services/v1/assume_account_role/([a-f0-9\-]+)", AdministrativeAssumeAccount ),
		( r"/services/v1/maintain_aws_account_pool", MaintainAWSAccountReserves ),
		( r"/services/v1/billing_watchdog", RunBillingWatchdogJob ),
		( r"/services/v1/bill_customers", RunMonthlyStripeBillingJob ),
		( r"/services/v1/perform_terraform_plan_on_fleet", PerformTerraformPlanOnFleet ),
		( r"/services/v1/dangerously_terraform_update_fleet", PerformTerraformUpdateOnFleet ),
		( r"/services/v1/update_managed_console_users_iam", UpdateIAMConsoleUserIAM ),
		( r"/services/v1/onboard_third_party_aws_account_plan", OnboardThirdPartyAWSAccountPlan ),
		( r"/services/v1/dangerously_finalize_third_party_aws_onboarding", OnboardThirdPartyAWSAccountApply ),
		( r"/services/v1/clear_s3_build_packages", ClearAllS3BuildPackages ),
		( r"/services/v1/dangling_resources/([a-f0-9\-]+)", CleanupDanglingResources ),
		( r"/services/v1/clear_stripe_invoice_drafts", ClearStripeInvoiceDrafts ),
	], **tornado_config)
	
def get_lambda_callback_endpoint( tornado_config ):
	if tornado_config["ngrok_enabled"] == "true":
		logit( "Setting up the ngrok tunnel to the local websocket server..." )
		ngrok_http_endpoint = tornado.ioloop.IOLoop.current().run_sync(
			set_up_ngrok_websocket_tunnel
		)
		
		return ngrok_http_endpoint.replace(
			"https://",
			"ws://"
		).replace(
			"http://",
			"ws://"
		) + "/ws/v1/lambdas/connectback"
		
	remote_ipv4_address = tornado.ioloop.IOLoop.current().run_sync(
		get_external_ipv4_address
	)
	return "ws://" + remote_ipv4_address + ":3333/ws/v1/lambdas/connectback"

if __name__ == "__main__":
	logit( "Starting the Refinery service...", "info" )
	on_start()
	
	is_debug = ( os.environ.get( "is_debug" ).lower() == "true" )
	
	# Generate tornado config
	tornado_config = get_tornado_app_config(
		is_debug
	)
	
	# Start API server
	app = make_app(
		tornado_config
	)
	server = tornado.httpserver.HTTPServer(
		app
	)
	server.bind(
		7777
	)
	
	# Start websocket server
	websocket_app = make_websocket_server(
		tornado_config
	)
	
	websocket_server = tornado.httpserver.HTTPServer(
		websocket_app
	)
	websocket_server.bind(
		3333
	)

	# Start scheduled heartbeats for WebSocket server
	tornado.ioloop.IOLoop.instance().add_timeout(
		datetime.timedelta(
			seconds=5
		),
		functools.partial(
			run_scheduled_heartbeat,
			tornado_config[ "websocket_router" ]
		)
	)

	Base.metadata.create_all( engine )
		
	# Resolve what our callback endpoint is, this is different in DEV vs PROD
	# one assumes you have an external IP address and the other does not (and
	# fixes the situation for you with ngrok).
	LAMBDA_CALLBACK_ENDPOINT = get_lambda_callback_endpoint(
		tornado_config
	)
	
	logit( "Lambda callback endpoint is " + LAMBDA_CALLBACK_ENDPOINT )
		
	server.start()
	websocket_server.start()
	tornado.ioloop.IOLoop.current().start()