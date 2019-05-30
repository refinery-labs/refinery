#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
import tornado.escape
import tornado.ioloop
import tornado.web
import subprocess
import traceback
import botocore
import datetime
import pystache
import logging
import hashlib
import random
import shutil
import stripe
import base64
import string
import boto3
import numpy
import struct
import uuid
import json
import yaml
import copy
import math
import time
import jwt
import sys
import os
import io

from tornado import gen
from datetime import timedelta
from tornado.web import asynchronous
from expiringdict import ExpiringDict
from botocore.exceptions import ClientError
from jsonschema import validate as validate_schema
from tornado.concurrent import run_on_executor, futures
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from email_validator import validate_email, EmailNotValidError

from models.initiate_database import *
from models.saved_lambda import SavedLambda
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

from botocore.client import Config

logging.basicConfig(
	stream=sys.stdout,
	level=logging.INFO
)

import StringIO
import zipfile

from expiringdict import ExpiringDict

reload( sys )
sys.setdefaultencoding( "utf8" )

EMPTY_ZIP_DATA = bytearray( "PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" )

# Initialize Stripe
stripe.api_key = os.environ.get( "stripe_api_key" )

# Cloudflare Access public keys
CF_ACCESS_PUBLIC_KEYS = []

# Pull list of allowed Access-Control-Allow-Origin values from environment var
allowed_origins = json.loads( os.environ.get( "access_control_allow_origins" ) )
			
def on_start():
	global LAMDBA_BASE_CODES, LAMBDA_BASE_LIBRARIES, LAMBDA_SUPPORTED_LANGUAGES, CUSTOM_RUNTIME_CODE, CUSTOM_RUNTIME_LANGUAGES, EMAIL_TEMPLATES, CUSTOMER_IAM_POLICY
	
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
		"php7.3",
	]
	
	LAMBDA_BASE_LIBRARIES = {
		"python2.7": [
			"redis",
		],
		"nodejs8.10": [],
		"php7.3": [],
	}
	
	LAMBDA_SUPPORTED_LANGUAGES = [
		"python2.7",
		"nodejs8.10",
		"php7.3",
	]
	
	CUSTOM_RUNTIME_CODE = ""
	
	CUSTOMER_IAM_POLICY = ""
	
	with open( "./install/refinery-customer-iam-policy.json", "r" ) as file_handler:
		CUSTOMER_IAM_POLICY = json.loads(
			file_handler.read()
		)
	
	with open( "./custom-runtime/base-src/bootstrap", "r" ) as file_handler:
		CUSTOM_RUNTIME_CODE = file_handler.read()

	for language_name, libraries in LAMBDA_BASE_LIBRARIES.iteritems():
		# Load Lambda base templates
		with open( "./lambda_bases/" + language_name, "r" ) as file_handler:
			LAMDBA_BASE_CODES[ language_name ] = file_handler.read()

# This is purely for sending emails as part of Refinery's
# regular operations (e.g. authentication via email code, etc).
SES_EMAIL_CLIENT = boto3.client(
	"ses",
	aws_access_key_id=os.environ.get( "aws_access_key" ),
	aws_secret_access_key=os.environ.get( "aws_secret_key" ),
	region_name=os.environ.get( "region_name" )
)

# This is another global Boto3 client because we need root access
# to pull the billing for all of our sub-accounts
COST_EXPLORER = boto3.client(
	"ce",
	aws_access_key_id=os.environ.get( "aws_access_key" ),
	aws_secret_access_key=os.environ.get( "aws_secret_key" ),
	region_name=os.environ.get( "region_name" )
)

# This client is used to assume role into all of our customer's
# AWS accounts as a root-priveleged support account ("DO_NOT_DELETE_REFINERY_SYSTEM_ACCOUNT")
STS_CLIENT = boto3.client(
	"sts",
	aws_access_key_id=os.environ.get( "aws_access_key" ),
	aws_secret_access_key=os.environ.get( "aws_secret_key" ),
	region_name=os.environ.get( "region_name" )
)

# The AWS organization API for provisioning new AWS sub-accounts
# for customers to use.
ORGANIZATION_CLIENT = boto3.client(
	"organizations",
	aws_access_key_id=os.environ.get( "aws_access_key" ),
	aws_secret_access_key=os.environ.get( "aws_secret_key" ),
	region_name=os.environ.get( "region_name" )
)

# For generating crytographically-secure random strings
def get_urand_password( length ):
    symbols = string.ascii_letters + string.digits
    return "".join([symbols[x * len(symbols) / 256] for x in struct.unpack("%dB" % (length,), os.urandom(length))])
    
"""
This is some poor-man's caching to greately speed up Boto3
client access times. We basically just cache and return the client
if it's less than the STS Assume Role age.

Basically this is critical when we do things like the S3 log pulling
because it does TONS of concurrent connections. Without the caching it
can take ~35 seconds to pull the logs, with the caching it takes ~5.
"""
BOTO3_CLIENT_CACHE = ExpiringDict(
	max_len=500,
	max_age_seconds=( int( os.environ.get( "assume_role_session_lifetime_seconds" ) ) - 60 )
)
def get_aws_client( client_type, credentials ):
	"""
	Take an AWS client type ("s3", "lambda", etc) and utilize
	STS to assume role into the customer's account and return
	a key and token for the admin service account ("DO_NOT_DELETE_REFINERY_SYSTEM_ACCOUNT")
	"""
	global BOTO3_CLIENT_CACHE
	
	cache_key = client_type + credentials[ "account_id" ] + credentials[ "region" ]
	
	if cache_key in BOTO3_CLIENT_CACHE:
		return BOTO3_CLIENT_CACHE[ cache_key ]
	
	# Generate the Refinery AWS management role ARN we are going to assume into
	sub_account_admin_role_arn = "arn:aws:iam::" + credentials[ "account_id" ] + ":role/DO_NOT_DELETE_REFINERY_SYSTEM_ACCOUNT"
	
	# We need to generate a random role session name
	role_session_name = "Refinery-Managed-Account-Support-" + get_urand_password( 12 )
	
	# Perform the assume role action
	assume_role_response = STS_CLIENT.assume_role(
		RoleArn=sub_account_admin_role_arn,
		RoleSessionName=role_session_name,
		DurationSeconds=int( os.environ.get( "assume_role_session_lifetime_seconds" ) )
	)
	
	# Remove non-JSON serializable part from response
	del assume_role_response[ "Credentials" ][ "Expiration" ]
	
	# Take the assume role credentials and use it to create a boto3 session
	boto3_session = boto3.Session(
		aws_access_key_id=assume_role_response[ "Credentials" ][ "AccessKeyId" ],
		aws_secret_access_key=assume_role_response[ "Credentials" ][ "SecretAccessKey" ],
		aws_session_token=assume_role_response[ "Credentials" ][ "SessionToken" ],
		region_name=credentials[ "region" ],
	)
	
	# Options for boto3 client
	client_options = {}
	
	# Custom configurations depending on the client type
	if client_type == "lambda":
		client_options[ "config" ] = Config(
			connect_timeout=50,
			read_timeout=( 60 * 15 )
		)
	elif client_type == "s3":
		client_options[ "config" ] = Config(
			max_pool_connections=( 1000 * 2 )
		)
	
	# Use the new boto3 session to create a boto3 client
	boto3_client = boto3_session.client(
		client_type,
		**client_options
	)
	
	# Store it in the cache for future access
	BOTO3_CLIENT_CACHE[ cache_key ] = boto3_client
	
	return boto3_client
		
def logit( message, message_type="info" ):
	# Attempt to parse the message as json
	# If we can then prettify it before printing
	try:
		message = json.dumps(
			message,
			sort_keys=True,
			indent=4,
			separators=( ",", ": " )
		)
	except:
		pass
	
	if message_type == "info":
		logging.info( message )
	elif message_type == "warn":
		logging.warn( message )
	elif message_type == "error":
		logging.error( message )
	elif message_type == "debug":
		logging.debug( message )
	else:
		logging.info( message )
	
class BaseHandler( tornado.web.RequestHandler ):
	def __init__( self, *args, **kwargs ):
		super( BaseHandler, self ).__init__( *args, **kwargs )
		self.set_header( "Access-Control-Allow-Headers", "Content-Type, X-CSRF-Validation-Header" )
		self.set_header( "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, HEAD" )
		self.set_header( "Access-Control-Allow-Credentials", "true" )
		self.set_header( "Access-Control-Max-Age", "600" )
		self.set_header( "X-Frame-Options", "deny" )
		self.set_header( "Content-Security-Policy", "default-src 'self'" )
		self.set_header( "X-XSS-Protection", "1; mode=block" )
		self.set_header( "X-Content-Type-Options", "nosniff" )
		self.set_header( "Cache-Control", "no-cache, no-store, must-revalidate" )
		self.set_header( "Pragma", "no-cache" )
		self.set_header( "Expires", "0" )
		
		# For caching the currently-authenticated user
		self.authenticated_user = None
    
	def initialize( self ):
		if "Origin" not in self.request.headers:
			return

		host_header = self.request.headers[ "Origin" ]

		# Identify if the request is coming from a domain that is in the whitelist
		# If it is, set the necessary CORS response header to allow the request to succeed.
		if host_header in allowed_origins:
			self.set_header( "Access-Control-Allow-Origin", host_header )
		
	def authenticate_user_id( self, user_id ):
		# Set authentication cookie
		self.set_secure_cookie(
			"session",
			json.dumps({
				"user_id": user_id,
			}),
			expires_days=int( os.environ.get( "cookie_expire_days" ) )
		)
		
	def is_owner_of_project( self, project_id ):
		# Check to ensure the user owns the project
		project = session.query( Project ).filter_by(
			id=project_id
		).first()
		
		# Iterate over project owners and see if one matches
		# the currently authenticated user
		is_owner = False
		
		for project_owner in project.users:
			if self.get_authenticated_user_id() == project_owner.id:
				is_owner = True
				
		return is_owner
		
	def get_authenticated_user_cloud_configurations( self ):
		"""
		This returns the cloud configurations for the current user.
		
		This mainly means things like AWS credentials, S3 buckets
		used for package builders, etc.
		
		This will return a list of configuration JSON objects. Note
		that in the beggining we will ALWAYS just use the first JSON
		object in the list because we don't support multiple AWS deploys
		yet.
		"""
		# Pull the authenticated user's organization
		user_organization = self.get_authenticated_user_org()
		
		if user_organization == None:
			return None
		
		# Returned list of JSON cloud config data
		cloud_configuration_list = []
		
		# Return the JSON objects for all AWS accounts
		for aws_account in user_organization.aws_accounts:
			cloud_configuration_list.append(
				aws_account.to_dict()
			)
			
		return cloud_configuration_list
		
	def get_authenticated_user_cloud_configuration( self ):
		"""
		This just returns the first cloud configuration. Short term use since we'll
		eventually be moving to a multiple AWS account deploy system.
		"""
		cloud_configurations = self.get_authenticated_user_cloud_configurations()
		
		if len( cloud_configurations ) > 0:
			return cloud_configurations[ 0 ]
		
		return False
		
	def get_authenticated_user_org( self ):
		# First we grab the organization ID
		authentication_user = self.get_authenticated_user()
		
		if authentication_user == None:
			return None
		
		# Get organization user is a part of
		user_org = session.query( Organization ).filter_by(
			id=authentication_user.organization_id
		).first()
		
		return user_org
		
	def get_authenticated_user_id( self ):
		# Get secure cookie data
		secure_cookie_data = self.get_secure_cookie(
			"session",
			max_age_days=int( os.environ.get( "cookie_expire_days" ) )
		)
		
		if secure_cookie_data == None:
			return None
			
		session_data = json.loads(
			secure_cookie_data
		)
		
		if not ( "user_id" in session_data ):
			return None
			
		return session_data[ "user_id" ]
		
	def get_authenticated_user( self ):
		"""
		Grabs the currently authenticated user
		
		This will be cached after the first call of
		this method,
		"""
		if self.authenticated_user != None:
			return self.authenticated_user
		
		user_id = self.get_authenticated_user_id()
		
		if user_id == None:
			return None
		
		# Pull related user
		authenticated_user = session.query( User ).filter_by(
			id=str( user_id )
		).first()
		
		self.authenticated_user = authenticated_user

		return authenticated_user
		
	def prepare( self ):
		"""
		/service/ path protection requiring a shared-secret to access them.
		"""
		if self.request.path.startswith( "/services/" ):
			services_auth_header = self.request.headers.get( "X-Service-Secret", None )
			services_auth_param = self.get_argument( "secret", None )
			
			service_secret = None
			if services_auth_header:
				service_secret = services_auth_header
			elif services_auth_param:
				service_secret = services_auth_param
				
			if os.environ.get( "service_shared_secret" ) != service_secret:
				self.error(
					"You are hitting a service URL, you MUST provide the shared secret in either a 'secret' parameter or the 'X-Service-Secret' header to use this.",
					"ACCESS_DENIED_SHARED_SECRET_REQUIRED"
				)
				return
		
		"""
		Cloudflare auth JWT validation
		"""
		if os.environ.get( "cf_enabled" ).lower() == "true":
			cf_authorization_cookie = self.get_cookie( "CF_Authorization" )
			
			if not cf_authorization_cookie:
				self.error(
					"Error, no Cloudflare Access 'CF_Authorization' cookie set.",
					"CF_ACCESS_NO_COOKIE"
				)
				return
				
			valid_token = False
			
			for public_key in CF_ACCESS_PUBLIC_KEYS:
				try:
					jwt.decode(
						cf_authorization_cookie,
						key=public_key,
						audience=os.environ.get( "cf_policy_aud" )
					)
					valid_token = True
				except:
					pass
			
			if not valid_token:
				self.error(
					"Error, Cloudflare Access verification check failed.",
					"CF_ACCESS_DENIED"
				)
				return
		
		csrf_validated = self.request.headers.get(
			"X-CSRF-Validation-Header",
			False
		)
		
		if not csrf_validated and self.request.method != "OPTIONS" and self.request.method != "GET" and not self.request.path in CSRF_EXEMPT_ENDPOINTS:
			self.error(
				"No CSRF validation header supplied!",
				"INVALID_CSRF"
			)
			raise gen.Return()
		
		self.json = False
		
		if self.request.body:
			try:
				json_data = json.loads(self.request.body)
				self.json = json_data
			except ValueError:
				pass

	def options(self):
		pass

	# Hack to stop Tornado from sending the Etag header
	def compute_etag( self ):
		return None

	def throw_404( self ):
		self.set_status(404)
		self.write("Resource not found")
		
	def on_finish( self ):
		session.close()

	def error( self, error_message, error_id ):
		self.set_status( 500 )
		logit(
			error_message,
			message_type="warn"
		)
		
		self.finish({
			"success": False,
			"msg": error_message,
			"code": error_id
		})
		
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

class TaskSpawner(object):
		def __init__(self, loop=None):
			self.executor = futures.ThreadPoolExecutor( 60 )
			self.loop = loop or tornado.ioloop.IOLoop.current()
			
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
		def _get_assume_role_credentials( role_arn, session_lifetime ):
			# Session lifetime must be a minimum of 15 minutes
			# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html#STS.Client.assume_role
			min_session_lifetime_seconds = 900
			if session_lifetime < min_session_lifetime_seconds:
				session_lifetime = min_session_lifetime_seconds
			
			role_session_name = "Refinery-Managed-Account-Support-" + get_urand_password( 12 )
			
			response = STS_CLIENT.assume_role(
				RoleArn=role_arn,
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
		def provision_new_sub_aws_account( self ):
			return TaskSpawner._provision_new_sub_aws_account()
			
		@staticmethod
		def _provision_new_sub_aws_account():
			# Create a temporary working directory for the work.
			# Even if there's some exception thrown during the process
			# we will still delete the underlying state.
			temporary_dir = "/tmp/" + str( uuid.uuid4() ) + "/"
			
			try:
				# Recursively copy files to the directory
				shutil.copytree(
					"/work/install/",
					temporary_dir
				)
				
				TaskSpawner.__provision_new_sub_aws_account(
					temporary_dir
				)
			finally:
				# Delete the temporary directory reguardless.
				shutil.rmtree( temporary_dir )
			
			return True
			
		@staticmethod
		def __provision_new_sub_aws_account( base_dir ):
			logit( "Provisioning a new AWS sub-account..." )
			
			# Used to keep all of the account details in one place
			# for later insert into the database
			account_details = {}
			
			# Create a unique ID for the Refinery AWS account
			account_details[ "id" ] = get_urand_password( 16 ).lower()
			
			# Generate and set some secrets
			account_details[ "refinery_customer_aws_console_username" ] = "refinery-customer"
			account_details[ "refinery_customer_aws_console_password" ] = get_urand_password( 128 )
			account_details[ "s3_bucket_suffix" ] = str( get_urand_password( 32 ) ).lower()
			account_details[ "redis_password" ] = get_urand_password( 64 )
			account_details[ "redis_prefix" ] = get_urand_password( 40 )
			account_details[ "email" ] = os.environ.get( "customer_aws_email_prefix" ) + account_details[ "id" ] + os.environ.get( "customer_aws_email_suffix" )
			
			# Create AWS sub-account
			logit( "Creating AWS sub-account '" + account_details[ "email" ] + "'..." )
			
			# Create sub-AWS account
			account_creation_response = TaskSpawner._create_aws_org_sub_account(
				account_details[ "id" ],
				account_details[ "email" ],
			)
			
			if account_creation_response == False:
				raise Exception( "Account creation failed, quitting out!" )
			
			account_details[ "account_name" ] = account_creation_response[ "account_name" ]
			account_details[ "account_id" ] = account_creation_response[ "account_id" ]
			
			logit( "Sub-account created! AWS account ID is " + account_details[ "account_id" ] + " and the name is '" + account_details[ "account_name" ] + "'" )
			
			# Generate ARN for the sub-account AWS administrator role
			sub_account_admin_role_arn = "arn:aws:iam::" + str( account_details[ "account_id" ] ) + ":role/" + os.environ.get( "customer_aws_admin_assume_role" )
			
			logit( "Sub-account role ARN is '" + sub_account_admin_role_arn + "'." )
			
			assumed_role_credentials = {}
			
			while True:
				logit( "Attempting to assume the sub-account's administrator role..." )
				
				try:
					# We then assume the administrator role for the sub-account we created
					assumed_role_credentials = TaskSpawner._get_assume_role_credentials(
						sub_account_admin_role_arn,
						3600 # One hour - TODO CHANGEME
					)
					break
				except botocore.exceptions.ClientError as boto_error:
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
				account_details[ "refinery_customer_aws_console_username" ],
				account_details[ "refinery_customer_aws_console_password" ]
			)
			
			logit( "Successfully minted a console user account!" )
			logit( "Writing Terraform input variables to file..." )
			
			# Write out the terraform configuration data
			terraform_configuration_data = {
				"session_token": assumed_role_credentials[ "session_token" ],
				"role_session_name": assumed_role_credentials[ "role_session_name" ],
				"assume_role_arn": sub_account_admin_role_arn,
				"access_key": assumed_role_credentials[ "access_key_id" ],
				"secret_key": assumed_role_credentials[ "secret_access_key" ],
				"region": os.environ.get( "region_name" ),
				"s3_bucket_suffix": account_details[ "s3_bucket_suffix" ],
				"redis_secrets": {
					"password": account_details[ "redis_password" ],
					"secret_prefix": account_details[ "redis_prefix" ],
				}
			}
			
			# Customer config path
			customer_aws_config_path = base_dir + "customer_config.json"
			
			# Write configuration data to a file for Terraform to use.
			with open( customer_aws_config_path, "w" ) as file_handler:
				file_handler.write(
					json.dumps(
						terraform_configuration_data
					)
				)
				
			logit( "Terraform input variables successfully written to disk. " )
			logit( "Waiting 60 seconds before running Terraform due to AWS propogation requirements..." )
			time.sleep( 60 )
			logit( "Finished waiting, applying Terraform plan to newly created account..." )
			logit( "Running 'terraform apply' to configure the account..." )
			
			# Terraform apply
			process_handler = subprocess.Popen(
				[
					base_dir + "terraform",
					"apply",
					"-auto-approve",
					"-var-file",
					customer_aws_config_path,
				],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False,
				universal_newlines=True,
				cwd=base_dir,
			)
			process_stdout, process_stderr = process_handler.communicate()
			
			if process_stderr.strip() != "":
				logit( "The Terraform provisioning has failed!" )
				# TODO - Notify us via an email alert to cancel the account.
				raise Exception( "Terraform provisioning failed!" )
			
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
				
			logit( "Adding AWS account to the database reserve pool..." )
			
			# Store the AWS account in the database
			new_aws_account = AWSAccount()
			new_aws_account.account_label = ""
			new_aws_account.account_id = terraform_provisioned_account_details[ "aws_account_id" ][ "value" ]
			new_aws_account.region = terraform_provisioned_account_details[ "aws_region" ][ "value" ]
			new_aws_account.s3_bucket_suffix = terraform_provisioned_account_details[ "s3_suffix" ][ "value" ]
			new_aws_account.iam_admin_username = account_details[ "refinery_customer_aws_console_username" ]
			new_aws_account.iam_admin_password = account_details[ "refinery_customer_aws_console_password" ]
			new_aws_account.redis_hostname = terraform_provisioned_account_details[ "redis_elastic_ip" ][ "value" ]
			new_aws_account.redis_password = account_details[ "redis_password" ]
			new_aws_account.redis_port = 6379
			new_aws_account.redis_secret_prefix = account_details[ "redis_prefix" ]
			new_aws_account.account_type = "MANAGED"
			new_aws_account.is_reserved_account = True
			new_aws_account.terraform_state = terraform_state
			new_aws_account.ssh_public_key = terraform_provisioned_account_details[ "refinery_redis_ssh_key_public_key_openssh" ][ "value" ]
			new_aws_account.ssh_private_key = terraform_provisioned_account_details[ "refinery_redis_ssh_key_private_key_pem" ][ "value" ]
			new_aws_account.aws_account_email = account_details[ "email" ]
			new_aws_account.terraform_state_versions = []
			
			# Create a new terraform state version
			terraform_state_version = TerraformStateVersion()
			terraform_state_version.terraform_state = terraform_state
			new_aws_account.terraform_state_versions.append(
				terraform_state_version
			)
			
			session.add( new_aws_account )
			session.commit()
			
			logit( "Added AWS account to the pool successfully!" )
			
			logit( "Freezing the account until it's used by someone..." )
			
			TaskSpawner._freeze_aws_account(
				new_aws_account.to_dict()
			)
			
			logit( "Account frozen successfully." )
			
			return True
		
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

			start_instance_response = ec2_client.start_instances(
				InstanceIds=ec2_instance_ids
			)
			
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
			
			logit( "Deleting AWS console user..." )
			
			# The only way to revoke an AWS Console user's session
			# is to delete the console user and create a new one.
			
			# Generate the IAM policy ARN
			iam_policy_arn = "arn:aws:iam::" + credentials[ "account_id" ] + ":policy/RefineryCustomerPolicy"
			
			# Generate a new user console password
			new_console_user_password = get_urand_password( 128 )
			
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
			
			# Attach the limiting IAM policy to it.
			attach_policy_response = iam_client.attach_user_policy(
				UserName=credentials[ "iam_admin_username" ],
				PolicyArn=iam_policy_arn
			)
			
			# Create the console user again.
			create_user_response = iam_client.create_login_profile(
				UserName=credentials[ "iam_admin_username" ],
				Password=new_console_user_password,
				PasswordResetRequired=False
			)
			
			# Update the console login in the database
			aws_account = session.query( AWSAccount ).filter_by(
				account_id=credentials[ "account_id" ]
			).first()
			aws_account.iam_admin_password = new_console_user_password
			session.commit()
			
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
			
			return False
			
		@staticmethod
		def send_account_freeze_email( aws_account_id, amount_accumulated, organization_admin_email ):
			response = SES_EMAIL_CLIENT.send_email(
				Source=os.environ.get( "ses_emails_from_email" ),
				Destination={
					"ToAddresses": [
						os.environ.get( "free_trial_freeze_alerts" ),
					]
				},
				Message={
					"Subject": {
						"Data": "[Freeze Alert] The Refinery AWS Account #" + aws_account_id + " has been frozen for going over its account limit!",
						"Charset": "UTF-8"
					},
					"Body": {
						"Html": {
							"Data": pystache.render(
								EMAIL_TEMPLATES[ "account_frozen_alert" ],
								{
									"aws_account_id": aws_account_id,
									"free_trial_billing_limit": os.environ.get( "free_trial_billing_limit" ),
									"amount_accumulated": amount_accumulated,
									"organization_admin_email": organization_admin_email,
								}
							),
							"Charset": "UTF-8"
						}
					}
				}
			)
		
		@run_on_executor
		def send_registration_confirmation_email( self, email_address, auth_token ):
			registration_confirmation_link = os.environ.get( "web_origin" ) + "/authentication/email/" + auth_token
			response = SES_EMAIL_CLIENT.send_email(
				Source=os.environ.get( "ses_emails_from_email" ),
				Destination={
					"ToAddresses": [
						email_address,
					]
				},
				Message={
					"Subject": {
						"Data": "RefineryLabs.io - Confirm your Refinery registration",
						"Charset": "UTF-8"
					},
					"Body": {
						"Text": {
							"Data": pystache.render(
								EMAIL_TEMPLATES[ "registration_confirmation_text" ],
								{
									"registration_confirmation_link": registration_confirmation_link,
								}
							),
							"Charset": "UTF-8"
						},
						"Html": {
							"Data": pystache.render(
								EMAIL_TEMPLATES[ "registration_confirmation" ],
								{
									"registration_confirmation_link": registration_confirmation_link,
								}
							),
							"Charset": "UTF-8"
						}
					}
				}
			)
	
		@run_on_executor
		def send_authentication_email( self, email_address, auth_token ):
			authentication_link = os.environ.get( "web_origin" ) + "/authentication/email/" + auth_token
			response = SES_EMAIL_CLIENT.send_email(
				Source=os.environ.get( "ses_emails_from_email" ),
				Destination={
					"ToAddresses": [
						email_address,
					]
				},
				Message={
					"Subject": {
						"Data": "RefineryLabs.io - Login by email confirmation",
						"Charset": "UTF-8"
					},
					"Body": {
						"Text": {
							"Data": pystache.render(
								EMAIL_TEMPLATES[ "authentication_email_text" ],
								{
									"email_authentication_link": authentication_link,
								}
							),
							"Charset": "UTF-8"
						},
						"Html": {
							"Data": pystache.render(
								EMAIL_TEMPLATES[ "authentication_email" ],
								{
									"email_authentication_link": authentication_link,
								}
							),
							"Charset": "UTF-8"
						}
					}
				}
			)
			
		@run_on_executor
		def stripe_create_customer( self, email, name ):
			# Create a customer in Stripe
			customer = stripe.Customer.create(
				email=email,
				name=name,
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
				
			return True
			
			# Delete the card from STripe
			delete_response = stripe.Customer.delete_source(
				stripe_customer_id,
				card_id
			)
			
			return cards[ "data" ]
			
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
			organizations = session.query( Organization )
			
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
			for organization in organizations:
				# If the organization is disabled we just skip it
				if organization.disabled == True:
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
				
				# Pull billing information for each AWS account
				for aws_account in organization.aws_accounts:
					# Skip the AWS account if it's not managed
					if aws_account.account_type != "MANAGED":
						continue
					
					billing_information = TaskSpawner._get_sub_account_billing_data(
						aws_account.account_id,
						start_date_string,
						end_date_string,
						"monthly",
						False
					)
					
					current_organization_invoice_data[ "aws_account_bills" ].append({
						"aws_account_label": aws_account.account_label,
						"aws_account_id": aws_account.account_id,
						"billing_information": billing_information,
					})
				
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
					
					customer_invoice = stripe.Invoice.create(
						**invoice_creation_params
					)
					
					if finalize_invoices_enabled:
						customer_invoice.send_invoice()
			
			# Notify finance department that they have an hour to review the
			response = SES_EMAIL_CLIENT.send_email(
				Source=os.environ.get( "ses_emails_from_email" ),
				Destination={
					"ToAddresses": [
						os.environ.get( "billing_alert_email" ),
					]
				},
				Message={
					"Subject": {
						"Data": "[URGENT][IMPORTANT]: Monthly customer invoice generation has completed. One hour to auto-finalization.",
						"Charset": "UTF-8"
					},
					"Body": {
						"Html": {
							"Data": "The monthly Stripe invoice generation has completed. You have <b>one hour</b> to review invoices before they go out to customers.<br /><a href=\"https://dashboard.stripe.com/invoices\"><b>Click here to review the generated invoices</b></a><br /><br />",
							"Charset": "UTF-8"
						}
					}
				}
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
			# Pull the configured free trial account limits
			free_trial_user_max_amount = float( os.environ.get( "free_trial_billing_limit" ) )
			
			# Iterate over the input list and pull the related accounts
			for aws_account_info in aws_account_running_cost_list:
				# Pull relevant AWS account
				aws_account = session.query( AWSAccount ).filter_by(
					account_id=aws_account_info[ "aws_account_id" ],
					is_reserved_account=False,
				).first()
				
				# If there's no related AWS account in the database
				# we just skip over it because it's likely a non-customer
				# AWS account
				if aws_account == None:
					continue
				
				# Pull related organization
				owner_organization = session.query( Organization ).filter_by(
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
	
		@run_on_executor
		def get_sub_account_month_billing_data( self, account_id, billing_month, use_cache ):
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
				billing_start_date,
				billing_end_date,
				"monthly",
				use_cache
			)
			
		@staticmethod
		def _get_sub_account_billing_data( account_id, start_date, end_date, granularity, use_cache ):
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
			
			# Markup multiplier
			markup_multiplier = 1 + ( int( os.environ.get( "mark_up_percent" ) ) / 100 )
			
			for service_breakdown_info in service_breakdown_list:
				# Remove branding words from service name
				service_name = service_breakdown_info[ "service_name" ]
				for aws_branding_word in remove_aws_branding_words:
					service_name = service_name.replace(
						aws_branding_word,
						""
					).strip()
				
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
			
			return_data[ "bill_total" ] = ( "%.2f" % total_amount )
			
			return return_data
		
		@staticmethod
		def _get_sub_account_service_breakdown_list( account_id, start_date, end_date, granularity, use_cache ):
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
			# Pull related AWS account and get the database ID for it
			aws_account = session.query( AWSAccount ).filter_by(
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
				billing_collection = session.query( CachedBillingCollection ).filter_by(
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
						
					return service_breakdown_list

			# Pull the raw billing data via the AWS CostExplorer API
			# Note that this returned data is not marked up.
			# This also costs us 1 cent each time we make this request
			# Which is why we implement caching for user billing.
			service_breakdown_list = TaskSpawner._api_get_sub_account_billing_data(
				account_id,
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
			
			session.add( new_billing_collection )
			session.commit()
			
			return service_breakdown_list
		
		@staticmethod
		def _api_get_sub_account_billing_data( account_id, start_date, end_date, granularity ):
			"""
			account_id: 994344292413
			start_date: 2017-05-01
			end_date: 2017-06-01
			granularity: "daily" || "hourly" || "monthly"
			"""
			metric_name = "NetUnblendedCost"
			
			usage_parameters = {
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
				"Metrics": [ metric_name ],
				"GroupBy": [
					{
						"Type": "DIMENSION",
						"Key": "SERVICE"
					}
				]
			}
			
			response = COST_EXPLORER.get_cost_and_usage(
				**usage_parameters
			)
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
			
			# Convert to dict/list if valid JSON
			try:
				full_response = json.loads(
					full_response
				)
			except:
				pass
			
			# Detect from response if it was an error
			is_error = False
			error_data = {}
			if type( full_response ) == dict and "errorMessage" in full_response and "errorType" in full_response and "stackTrace" in full_response:
				is_error = True
				error_data = {
					"message": full_response[ "errorMessage" ],
					"type": full_response[ "errorType" ],
					"trace": full_response[ "stackTrace" ]
				}
			
			# Null response data
			if is_error:
				full_response = False
			
			del response[ "Payload" ]
			
			function_error = False
			
			if "FunctionError" in response:
				function_error = response[ "FunctionError" ]
			
			log_output = base64.b64decode(
				response[ "LogResult" ]
			)
			
			# Will be filled with parsed lines
			if "START RequestId:" in log_output:
				log_lines = log_output.split( "\n" )
				
			# Mark truncated if logs are not complete
			truncated = True
			if( "START RequestId: " in log_output and "END RequestId: " in log_output ):
				truncated = False

			return {
				"truncated": truncated,
				"arn": arn,
				"version": response[ "ExecutedVersion" ],
				"response": full_response,
				"request_id": response[ "ResponseMetadata" ][ "RequestId" ],
				"status_code": response[ "StatusCode" ],
				"retries": response[ "ResponseMetadata" ][ "RetryAttempts" ],
				"logs": log_output,
				"is_error": is_error,
				"error": error_data
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
		def build_lambda( credentials, language, code, libraries ):
			logit( "Building Lambda " + language + " with libraries: " + str( libraries ), "info" )
			if not ( language in LAMBDA_SUPPORTED_LANGUAGES ):
				raise Exception( "Error, this language '" + language + "' is not yet supported by refinery!" )
			
			if language == "python2.7":
				package_zip_data = TaskSpawner._build_python27_lambda( credentials, code, libraries )
			elif language == "php7.3":
				package_zip_data = TaskSpawner._build_php_73_lambda( credentials, code, libraries )
			elif language == "nodejs8.10":
				package_zip_data = TaskSpawner._build_nodejs_810_lambda( credentials, code, libraries )
				
			return package_zip_data
			
		@run_on_executor
		def deploy_aws_lambda( self, credentials, func_name, language, description, role_name, code, libraries, timeout, memory, vpc_config, environment_variables, tags_dict, layers ):
			"""
			Here we do caching to see if we've done this exact build before
			(e.g. the same language, code, and libraries). If we have an the
			previous zip package is still in S3 we can just return that.
			
			The zip key is {{SHA256_OF_LANG-CODE-LIBRARIES}}.zip
			"""
			# Generate libraries object for now until we modify it to be a dict/object
			libraries_object = {}
			for library in libraries:
				libraries_object[ str( library ) ] = "latest"
				
			# Generate SHA256 hash input for caching key
			hash_input = language + "-" + code + "-" + json.dumps( libraries_object, sort_keys=True )
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
					language,
					code,
					libraries
				)
				
				# Write it the cache
				s3_client.put_object(
					Key=s3_package_zip_path,
					Bucket=credentials[ "lambda_packages_bucket" ],
					Body=lambda_zip_package_data,
				)
			
			return TaskSpawner._deploy_aws_lambda(
				credentials,
				func_name,
				language,
				description,
				role_name,
				s3_package_zip_path,
				timeout,
				memory,
				vpc_config,
				environment_variables,
				tags_dict,
				layers
			)

		@staticmethod
		def _deploy_aws_lambda( credentials, func_name, language, description, role_name, s3_package_zip_path, timeout, memory, vpc_config, environment_variables, tags_dict, layers ):
			if language in CUSTOM_RUNTIME_LANGUAGES:
				language = "provided"

			# Generate environment variables data structure
			env_data = {}
			for env_pair in environment_variables:
				env_data[ env_pair[ "key" ] ] = env_pair[ "value" ]
				
			# Create Lambda client
			lambda_client = get_aws_client(
				"lambda",
				credentials
			)
			
			try:
				# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.create_function
				response = lambda_client.create_function(
					FunctionName=func_name,
					Runtime=language,
					Role=role_name,
					Handler="lambda._init",
					Code={
						"S3Bucket": credentials[ "lambda_packages_bucket" ],
						"S3Key": s3_package_zip_path,
					},
					Description=description,
					Timeout=int(timeout),
					MemorySize=int(memory),
					Publish=True,
					VpcConfig=vpc_config,
					Environment={
						"Variables": env_data
					},
					Tags=tags_dict,
					Layers=layers,
				)
			except ClientError as e:
				if e.response[ "Error" ][ "Code" ] == "ResourceConflictException":
					# Delete the existing lambda
					delete_response = TaskSpawner._delete_aws_lambda(
						credentials,
						func_name
					)
					
					# Now create it since we're clear
					return TaskSpawner._deploy_aws_lambda(
						credentials,
						func_name,
						language,
						description,
						role_name,
						s3_package_zip_path,
						timeout,
						memory,
						vpc_config,
						environment_variables,
						tags_dict,
						layers
					)
				else:
					logit( "Exception occured: ", "error" )
					logit( e, "error" )
					return False
			
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
				raise "Build ID " + build_id + " failed with status code '" + build_status + "'!"
			
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
				
			composer_json_template = {
				"require": libraries_object,
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
							"composer install"
						]
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
				
				# Write the package.json
				composer_json = zipfile.ZipInfo(
					"composer.json"
				)
				composer_json.external_attr = 0777 << 16L
				zip_file_handler.writestr(
					composer_json,
					json.dumps(
						composer_json_template
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
		def _build_php_73_lambda( credentials, code, libraries ):
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "php7.3" ]
			
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
		def _build_nodejs_810_lambda( credentials, code, libraries ):
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "nodejs8.10" ]
			
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
		def _build_python27_lambda( credentials, code, libraries ):
			"""
			Build Lambda package zip and return zip data
			"""
			
			"""
			Inject base libraries (e.g. redis) into lambda
			and the init code.
			"""

			# Get customized base code
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "python2.7" ]
			
			for init_library in LAMBDA_BASE_LIBRARIES[ "python2.7" ]:
				if not init_library in libraries:
					libraries.append(
						init_library
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
					"lambda.py"
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
			
		@run_on_executor
		def create_cloudwatch_rule( self, credentials, id, name, schedule_expression, description, input_dict ):
			events_client = get_aws_client(
				"events",
				credentials,
			)
			
			# Events role ARN is able to be generated off of the account ID
			# The role name should be the same for all accounts.
			events_role_arn = "arn:aws:iam::" + str( credentials[ "account_id" ] ) + ":role/refinery_default_aws_cloudwatch_role"
			
			response = events_client.put_rule(
				Name=name,
				ScheduleExpression=schedule_expression, # cron(0 20 * * ? *) or rate(5 minutes)
				State="ENABLED",
				Description=description,
				RoleArn=events_role_arn,
			)
			
			return {
				"id": id,
				"name": name,
				"arn": response[ "RuleArn" ],
				"input_dict": input_dict,
			}
			
		@run_on_executor
		def add_rule_target( self, credentials, rule_name, target_id, target_arn, input_dict ):
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
					input_dict
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
				Name=topic_name
			)
			
			return {
				"id": id,
				"name": topic_name,
				"arn": response[ "TopicArn" ],
				"topic_name": topic_name
			}
			
		@run_on_executor
		def subscribe_lambda_to_sns_topic( self, credentials, topic_name, topic_arn, lambda_arn ):
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
		def create_sqs_queue( self, credentials, id, queue_name, content_based_deduplication, batch_size ):
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
							"VisibilityTimeout": str( 300 + 10 ), # Lambda max time plus ten seconds
						}
					)
					
					queue_deleted = True
				except sqs_client.exceptions.QueueDeletedRecently:
					logit( "SQS queue was deleted too recently, trying again in ten seconds..." )
					
					time.sleep( 10 )
			
			sqs_arn = "arn:aws:sqs:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + queue_name
			
			return {
				"id": id,
				"queue_name": queue_name,
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
		def get_lambda_cloudwatch_logs( self, credentials, arn ):
			cloudwatch_logs_client = get_aws_client(
				"logs",
				credentials
			)
			
			"""
			Pull the full logs from CloudWatch
			"""
			arn_parts = arn.split( ":" )
			lambda_name = arn_parts[ -1 ]
			log_group_name = "/aws/lambda/" + lambda_name
			
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
		def delete_lambda( self, credentials, id, type, name, arn ):
			return TaskSpawner._delete_lambda( credentials, id, type, name, arn )
			
		@staticmethod
		def _delete_lambda( credentials, id, type, name, arn ):
			lambda_client = get_aws_client(
				"lambda",
				credentials
			)
			
			was_deleted = False
			try:
				response = lambda_client.delete_function(
					FunctionName=arn,
				)
				was_deleted = True
			except ClientError as e:
				if e.response[ "Error" ][ "Code" ] != "ResourceNotFoundException":
					raise
				pass
			
			return {
				"id": id,
				"type": type,
				"name": name,
				"arn": arn,
				"deleted": was_deleted,
			}
			
		@run_on_executor
		def delete_sns_topic( self, credentials, id, type, name, arn ):
			return TaskSpawner._delete_sns_topic( credentials, id, type, name, arn )
			
		@staticmethod
		def _delete_sns_topic( credentials, id, type, name, arn ):
			sns_client = get_aws_client(
				"sns",
				credentials,
			)
			
			was_deleted = False
			
			try:
				response = sns_client.delete_topic(
					TopicArn=arn,
				)
				was_deleted = True
			except ClientError as e:
				if e.response[ "Error" ][ "Code" ] != "ResourceNotFoundException":
					raise
			
			return {
				"id": id,
				"type": type,
				"name": name,
				"arn": arn,
				"deleted": was_deleted,
			}
			
		@run_on_executor
		def delete_sqs_queue( self, credentials, id, type, name, arn ):
			return TaskSpawner._delete_sqs_queue( credentials, id, type, name, arn )
			
		@staticmethod
		def _delete_sqs_queue( credentials, id, type, name, arn ):
			sqs_client = get_aws_client(
				"sqs",
				credentials,
			)
			
			was_deleted = False
			
			try:
				queue_url_response = sqs_client.get_queue_url(
					QueueName=name,
				)
				
				response = sqs_client.delete_queue(
					QueueUrl=queue_url_response[ "QueueUrl" ],
				)
			except ClientError as e:
				if e.response[ "Error" ][ "Code" ] != "ResourceNotFoundException":
					raise
			
			return {
				"id": id,
				"type": type,
				"name": name,
				"arn": arn,
				"deleted": was_deleted,
			}
			
		@run_on_executor
		def delete_schedule_trigger( self, credentials, id, type, name, arn ):
			return TaskSpawner._delete_schedule_trigger( credentials, id, type, name, arn )
			
		@staticmethod
		def _delete_schedule_trigger( credentials, id, type, name, arn ):
			events_client = get_aws_client(
				"events",
				credentials
			)
			
			was_deleted = False
			try:
				list_rule_targets_response = events_client.list_targets_by_rule(
					Rule=name,
				)
				
				target_ids = []
				
				for target_item in list_rule_targets_response[ "Targets" ]:
					target_ids.append(
						target_item[ "Id" ]
					)
	
				# If there are some targets, delete them, else skip this.
				if len( target_ids ) > 0:
					remove_targets_response = events_client.remove_targets(
						Rule=name,
						Ids=target_ids
					)
				
				response = events_client.delete_rule(
					Name=name,
				)
				
				was_deleted = True
			except ClientError as e:
				if e.response[ "Error" ][ "Code" ] != "ResourceNotFoundException":
					raise
			
			return {
				"id": id,
				"type": type,
				"name": name,
				"arn": arn,
				"deleted": was_deleted,
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
				}
			)
			
			return {
				"id": response[ "id" ],
				"name": response[ "name" ],
				"description": response[ "description" ],
				"version": response[ "version" ]
			}
			
		@run_on_executor
		def delete_rest_api( self, credentials, rest_api_id ):
			api_gateway_client = get_aws_client(
				"apigateway",
				credentials
			)
			
			response = api_gateway_client.delete_rest_api(
				restApiId=rest_api_id,
			)
			
			return {
				"id": rest_api_id,
			}
			
		@run_on_executor
		def delete_rest_api_resource( self, credentials, rest_api_id, resource_id ):
			api_gateway_client = get_aws_client(
				"apigateway",
				credentials
			)
			
			response = api_gateway_client.delete_resource(
				restApiId=rest_api_id,
				resourceId=resource_id,
			)
			
			return {
				"rest_api_id": rest_api_id,
				"resource_id": resource_id
			}
			
		@run_on_executor
		def delete_rest_api_resource_method( self, credentials, rest_api_id, resource_id, method ):
			api_gateway_client = get_aws_client(
				"apigateway",
				credentials
			)
			
			try:
				response = api_gateway_client.delete_method(
					restApiId=rest_api_id,
					resourceId=resource_id,
					httpMethod=method,
				)
			except:
				logit( "Exception occurred while deleting method '" + method + "'!" )
				pass
			
			return {
				"rest_api_id": rest_api_id,
				"resource_id": resource_id,
				"method": method
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
			
			logit( "Deployment response: " )
			logit( deployment_response )
			
			return {
				"id": rest_api_id,
				"stage_name": stage_name,
				"deployment_id": deployment_id,
			}
			
		@run_on_executor
		def get_resources( self, credentials, rest_api_id ):
			api_gateway_client = get_aws_client(
				"apigateway",
				credentials
			)
			
			response = api_gateway_client.get_resources(
				restApiId=rest_api_id,
				limit=500
			)
			
			return response[ "items" ]
			
		@run_on_executor
		def get_stages( self, credentials, rest_api_id ):
			api_gateway_client = get_aws_client(
				"apigateway",
				credentials
			)
			
			response = api_gateway_client.get_stages(
				restApiId=rest_api_id
			)
			
			return response[ "item" ]
			
		@run_on_executor
		def delete_stage( self, credentials, rest_api_id, stage_name ):
			api_gateway_client = get_aws_client(
				"apigateway",
				credentials
			)
			
			response = api_gateway_client.delete_stage(
				restApiId=rest_api_id,
				stageName=stage_name
			)
			
			return {
				"rest_api_id": rest_api_id,
				"stage_name": stage_name
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
			
def get_random_node_id():
	return "n" + str( uuid.uuid4() ).replace( "-", "" )
	
def get_random_id( length ):
	return "".join(
		random.choice(
			string.ascii_letters + string.digits
		) for _ in range( length )
	)

def get_random_deploy_id():
	return "_RFN" + get_random_id( 6 )

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
				"arn": {
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
		
		# Try to parse Lambda input as JSON
		try:
			self.json[ "input_data" ] = json.loads(
				self.json[ "input_data" ]
			)
		except:
			pass
		
		logit( "Executing Lambda..." )
		lambda_result = yield local_tasks.execute_aws_lambda(
			self.get_authenticated_user_cloud_configuration(),
			self.json[ "arn" ],
			self.json[ "input_data" ],
		)
		
		self.write({
			"success": True,
			"result": lambda_result
		})
		
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
		
		lambda_info = yield deploy_lambda(
			credentials,
			random_node_id,
			random_node_id,
			self.json[ "language" ],
			self.json[ "code" ],
			self.json[ "libraries" ],
			self.json[ "max_execution_time" ],
			self.json[ "memory" ], # MB of execution memory
			{
				"then": [],
				"exception": [],
				"fan-out": [],
				"else": [],
				"fan-in": [],
				"if": []
			},
			"REGULAR",
			"SHOULD_NEVER_HAPPEN_TMP_LAMBDA_RUN", # Doesn't matter no logging is enabled
			"LOG_NONE",
			self.json[ "environment_variables" ], # Env list
			self.json[ "layers" ]
		)
		
		# Try to parse Lambda input as JSON
		try:
			self.json[ "input_data" ] = json.loads(
				self.json[ "input_data" ]
			)
		except:
			pass
		
		logit( "Executing Lambda..." )
		lambda_result = yield local_tasks.execute_aws_lambda(
			self.get_authenticated_user_cloud_configuration(),
			lambda_info[ "arn" ],
			{
				"_refinery": {
					"throw_exceptions_fully": True,
					"input_data": self.json[ "input_data" ]
				}
			},
		)

		logit( "Deleting Lambda..." )
		
		# Now we delete the lambda, don't yield because we don't need to wait
		delete_result = local_tasks.delete_aws_lambda(
			self.get_authenticated_user_cloud_configuration(),
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
	
@gen.coroutine
def deploy_lambda( credentials, id, name, language, code, libraries, max_execution_time, memory, transitions, execution_mode, execution_pipeline_id, execution_log_level, environment_variables, layers ):
	"""
	Here we build the default required environment variables.
	"""
	all_environment_vars = copy.copy( environment_variables )
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
		"value": execution_pipeline_id,
	})
	
	all_environment_vars.append({
		"key": "LOG_BUCKET_NAME",
		"value": credentials[ "logs_bucket" ],
	})

	all_environment_vars.append({
		"key": "PIPELINE_LOGGING_LEVEL",
		"value": execution_log_level,
	})
	
	all_environment_vars.append({
		"key": "EXECUTION_MODE",
		"value": execution_mode,
	})
	
	all_environment_vars.append({
		"key": "TRANSITION_DATA",
		"value": json.dumps(
			transitions
		),
	})

	logit(
		"Deploying '" + name + "' Lambda package to production..."
	)
	
	lambda_role = "arn:aws:iam::" + str( credentials[ "account_id" ] ) + ":role/refinery_default_aws_lambda_role"
	
	# Add the custom runtime layer in all cases
	if language == "nodejs8.10":
		layers.append(
			"arn:aws:lambda:" + str( credentials[ "region" ] ) + ":" + str( credentials[ "account_id" ] ) + ":layer:refinery-node810-custom-runtime:1"
		)
	elif language == "php7.3":
		layers.append(
			"arn:aws:lambda:" + str( credentials[ "region" ] ) + ":" + str( credentials[ "account_id" ] ) + ":layer:refinery-php73-custom-runtime:1"
		)

	deployed_lambda_data = yield local_tasks.deploy_aws_lambda(
		credentials,
		name,
		language,
		"AWS Lambda deployed via refinery",
		lambda_role,
		code,
		libraries,
		max_execution_time, # Max AWS execution time
		memory, # MB of execution memory
		{}, # VPC data
		all_environment_vars,
		{
			"refinery_id": id,
		},
		layers
	)
	
	raise gen.Return({
		"id": id,
		"name": name,
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
	
@gen.coroutine
def deploy_diagram( credentials, project_name, project_id, diagram_data, project_config ):
	"""
	Deploy the diagram to AWS
	"""
	
	"""
	Process workflow relationships and tag Lambda
	nodes with an array of transitions.
	"""
	
	# Random ID to keep deploy ARNs unique
	# TODO do more research into collision probability
	unique_deploy_id = get_random_deploy_id()
	
	# First just set an empty array for each lambda node
	for workflow_state in diagram_data[ "workflow_states" ]:
		# Update all of the workflow states with new random deploy ID
		if "name" in workflow_state:
			workflow_state[ "name" ] += unique_deploy_id
		# Edge case for SNS topics - TODO should be fixed so that SNS topics have "name" like any other node
		if "topic_name" in workflow_state:
			workflow_state[ "topic_name" ] += unique_deploy_id
		
		# If there are environment variables in project_config, add them to the Lambda node data
		if workflow_state[ "type" ] == "lambda":
			if workflow_state[ "id" ] in project_config[ "environment_variables" ]:
				workflow_state[ "environment_variables" ] = project_config[ "environment_variables" ][ workflow_state[ "id" ] ]
			else:
				workflow_state[ "environment_variables" ] = []
		
		if workflow_state[ "type" ] == "lambda" or workflow_state[ "type" ] == "api_endpoint":
			# Set up default transitions data
			workflow_state[ "transitions" ] = {}
			workflow_state[ "transitions" ][ "if" ] = []
			workflow_state[ "transitions" ][ "else" ] = []
			workflow_state[ "transitions" ][ "exception" ] = []
			workflow_state[ "transitions" ][ "then" ] = []
			workflow_state[ "transitions" ][ "fan-out" ] = []
			workflow_state[ "transitions" ][ "fan-in" ] = []
		
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

		lambda_node_deploy_futures.append({
			"id": lambda_node[ "id" ],
			"name": lambda_safe_name,
			"type": lambda_node[ "type" ],
			"future": deploy_lambda(
				credentials,
				lambda_node[ "id" ],
				lambda_safe_name,
				lambda_node[ "language" ],
				lambda_node[ "code" ],
				lambda_node[ "libraries" ],
				lambda_node[ "max_execution_time" ],
				lambda_node[ "memory" ],
				lambda_node[ "transitions" ],
				"REGULAR",
				project_id,
				project_config[ "logging" ][ "level" ],
				lambda_node[ "environment_variables" ],
				lambda_node[ "layers" ],
			)
		})
		
	"""
	Deploy all API Endpoints to production
	"""
	api_endpoint_node_deploy_futures = []
	
	for api_endpoint_node in api_endpoint_nodes:
		api_endpoint_safe_name = get_lambda_safe_name( api_endpoint_node[ "name" ] )
		logit( "Deploying API Endpoint '" + api_endpoint_safe_name + "'..." )
		api_endpoint_node_deploy_futures.append({
			"id": api_endpoint_node[ "id" ],
			"name": get_lambda_safe_name( api_endpoint_node[ "name" ] ),
			"type": api_endpoint_node[ "type" ],
			"future": deploy_lambda(
				credentials,
				api_endpoint_node[ "id" ],
				api_endpoint_safe_name,
				"python2.7",
				"",
				[],
				30,
				512,
				api_endpoint_node[ "transitions" ],
				"API_ENDPOINT",
				project_id,
				project_config[ "logging" ][ "level" ],
				[],
				[]
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
				schedule_trigger_node[ "input_dict" ],
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
				sqs_queue_node[ "content_based_deduplication" ],
				sqs_queue_node[ "batch_size" ] # Not used, passed along
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
				sns_topic_node[ "topic_name" ],
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
		
		# We need to create an API gateway
		logit( "Deploying API Gateway for API Endpoint(s)..." )
		
		# Create a new API Gateway if one does not already exist
		if api_gateway_id == False:
			rest_api_name = get_lambda_safe_name( project_name )
			create_gateway_result = yield local_tasks.create_rest_api(
				credentials,
				rest_api_name,
				rest_api_name, # Human readable name, just do the ID for now
				"1.0.0"
			)
			
			api_gateway_id = create_gateway_result[ "id" ]
			
			# Update project config
			project_config[ "api_gateway" ][ "gateway_id" ] = api_gateway_id
		
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
					
					api_route_futures.append(
						create_lambda_api_route(
							credentials,
							api_gateway_id,
							workflow_state[ "http_method" ],
							workflow_state[ "api_path" ],
							deployed_api_endpoint[ "name" ],
							True
						)
					)
					
		logit( "Waiting until all routes are deployed..." )
		yield api_route_futures
		
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
				workflow_state[ "name" ] = deployed_sqs_queue[ "queue_name" ]
				workflow_state[ "queue_name" ] = deployed_sqs_queue[ "queue_name" ]
				
	# Update SNS topics with arn
	for deployed_sns_topic in deployed_sns_topics:
		for workflow_state in diagram_data[ "workflow_states" ]:
			if workflow_state[ "id" ] == deployed_sns_topic[ "id" ]:
				workflow_state[ "arn" ] = deployed_sns_topic[ "arn" ]
				workflow_state[ "name" ] = deployed_sns_topic[ "topic_name" ]
				workflow_state[ "topic_name" ] = deployed_sns_topic[ "topic_name" ]
	
	
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
				schedule_trigger_pair[ "scheduled_trigger" ][ "input_dict" ]
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
				sqs_queue_trigger[ "sqs_queue_trigger" ][ "batch_size" ]
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
				sns_topic_trigger[ "sns_topic_trigger" ][ "topic_name" ],
				sns_topic_trigger[ "sns_topic_trigger" ][ "arn" ],
				sns_topic_trigger[ "target_lambda" ][ "arn" ],
			)
		)
	
	# Wait till are triggers are set up
	deployed_schedule_trigger_targets = yield schedule_trigger_targeting_futures
	sqs_queue_trigger_targets = yield sqs_queue_trigger_targeting_futures
	sns_topic_trigger_targets = yield sns_topic_trigger_targeting_futures
	
	raise gen.Return({
		"success": True,
		"project_name": project_name,
		"project_id": project_id,
		"deployment_diagram": diagram_data,
		"project_config": project_config
	})
		
class SavedLambdaCreate( BaseHandler ):
	@authenticated
	def post( self ):
		"""
		Create a Lambda to save for later use.
		"""
		schema = {
			"type": "object",
			"properties": {
				"name": {
					"type": "string",
				},
				"description": {
					"type": "string",
				},
				"code": {
					"type": "string",
				},
				"language": {
					"type": "string",
				},
				"libraries": {
					"type": "array",
				},
				"memory": {
					"type": "integer",
					"minimum": 128,
					"maximum": 3008,
					"multipleOf": 64
				},
				"max_execution_time": {
					"type": "integer",
					"minimum": 1,
					"maximum": 900
				},
			},
			"required": [
				"name",
				"description",
				"code",
				"language",
				"libraries",
				"memory",
				"max_execution_time"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Saving Lambda data..." )
		
		new_lambda = SavedLambda()
		new_lambda.name = self.json[ "name" ]
		new_lambda.language = self.json[ "language" ]
		new_lambda.libraries = json.dumps(
			self.json[ "libraries" ]
		)
		new_lambda.code = self.json[ "code" ]
		new_lambda.memory = self.json[ "memory" ]
		new_lambda.max_execution_time = self.json[ "max_execution_time" ]
		new_lambda.description = self.json[ "description" ]
		new_lambda.user_id = self.get_authenticated_user_id()

		session.add( new_lambda )
		session.commit()
		
		self.write({
			"success": True,
			"id": new_lambda.id
		})
		
class SavedLambdaSearch( BaseHandler ):
	@authenticated
	def post( self ):
		"""
		Free text search of saved Lambda, returns matching results.
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
		
		logit( "Searching saved Lambdas..." )
		
		# Get user's saved lambdas and search through them
		saved_lambdas = session.query( SavedLambda ).filter_by(
			user_id=self.get_authenticated_user_id()
		).all()
		
		# List of already returned result IDs
		existing_ids = []
		
		# List of results
		results_list = []
		
		# Searchable attributes
		searchable_attributes = [
			"name",
			"description"
		]
		
		# Search and add results in order of the searchable attributes
		for searchable_attribute in searchable_attributes:
			for saved_lambda in saved_lambdas:
				if self.json[ "query" ].lower() in getattr( saved_lambda, searchable_attribute ).lower() and not ( saved_lambda.id in existing_ids ):
					# Add to results
					results_list.append(
						saved_lambda.to_dict()
					)
					
					# Add to existing IDs so we don't have duplicates
					existing_ids.append(
						saved_lambda.id
					)
		
		self.write({
			"success": True,
			"results": results_list
		})
		
class SavedLambdaDelete( BaseHandler ):
	@authenticated
	@gen.coroutine
	def delete( self ):
		"""
		Delete a saved Lambda
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
		
		logit( "Deleting Lambda data..." )
		
		session.query( SavedLambda ).filter_by(
			user_id=self.get_authenticated_user_id(),
			id=self.json[ "id" ]
		).delete()
		
		session.commit()
		
		self.write({
			"success": True
		})

@gen.coroutine
def teardown_infrastructure( credentials, teardown_nodes ):
	"""
	[
		{
			"id": {{node_id}},
			"arn": {{production_resource_arn}},
			"name": {{node_name}},
			"type": {{node_type}},
		}
	]
	"""
	teardown_operation_futures = []
	
	for teardown_node in teardown_nodes:
		# Skip if the node doesn't exist
		# TODO move this client side, it's silly here.
		if "exists" in teardown_node and teardown_node[ "exists" ] == False:
			continue
		
		if teardown_node[ "type" ] == "lambda" or teardown_node[ "type" ] == "api_endpoint":
			teardown_operation_futures.append(
				local_tasks.delete_lambda(
					credentials,
					teardown_node[ "id" ],
					teardown_node[ "type" ],
					teardown_node[ "name" ],
					teardown_node[ "arn" ],
				)
			)
		elif teardown_node[ "type" ] == "sns_topic":
			teardown_operation_futures.append(
				local_tasks.delete_sns_topic(
					credentials,
					teardown_node[ "id" ],
					teardown_node[ "type" ],
					teardown_node[ "name" ],
					teardown_node[ "arn" ],
				)
			)
		elif teardown_node[ "type" ] == "sqs_queue":
			teardown_operation_futures.append(
				local_tasks.delete_sqs_queue(
					credentials,
					teardown_node[ "id" ],
					teardown_node[ "type" ],
					teardown_node[ "name" ],
					teardown_node[ "arn" ],
				)
			)
		elif teardown_node[ "type" ] == "schedule_trigger":
			teardown_operation_futures.append(
				local_tasks.delete_schedule_trigger(
					credentials,
					teardown_node[ "id" ],
					teardown_node[ "type" ],
					teardown_node[ "name" ],
					teardown_node[ "arn" ],
				)
			)
		elif teardown_node[ "type" ] == "api_gateway":
			teardown_operation_futures.append(
				strip_api_gateway(
					credentials,
					teardown_node[ "rest_api_id" ],
				)
			)
	
	teardown_operation_results = yield teardown_operation_futures
	
	raise gen.Return( teardown_operation_results )

class InfraTearDown( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		teardown_nodes = self.json[ "teardown_nodes" ]

		teardown_operation_results = yield teardown_infrastructure(
			self.get_authenticated_user_cloud_configuration(),
			teardown_nodes
		)
		
		# Delete our logs
		# No need to yield till it completes
		delete_logs(
			self.get_authenticated_user_cloud_configuration(),
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
						self.get_authenticated_user_cloud_configuration(),
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
						self.get_authenticated_user_cloud_configuration(),
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
						self.get_authenticated_user_cloud_configuration(),
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
						self.get_authenticated_user_cloud_configuration(),
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
		
class SaveProject( BaseHandler ):
	@authenticated
	@gen.coroutine
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
					raise gen.Return()
		
		# Check if project already exists
		if project_id:
			previous_project = session.query( Project ).filter_by(
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
				raise gen.Return()
		
		# If there is a previous project and the name doesn't match, update it.
		if previous_project and previous_project.name != project_name:
			previous_project.name = project_name
			session.commit()
		
		# If there's no previous project, create a new one
		if previous_project == None:
			previous_project = Project()
			previous_project.name = diagram_data[ "name" ]
			
			# Add the user to the project so they can access it
			previous_project.users.append(
				self.authenticated_user
			)
			
			session.add( previous_project )
			session.commit()
			
			# Set project ID to newly generated ID
			project_id = previous_project.id
		
		# If project version isn't set we'll update it to be an incremented version
		# from the latest saved version.
		if project_version == False:
			latest_project_version = session.query( ProjectVersion ).filter_by(
				project_id=project_id
			).order_by( ProjectVersion.version.desc() ).first()

			if latest_project_version == None:
				project_version = 1
			else:
				project_version = ( latest_project_version.version + 1 )
		else:
			previous_project_version = session.query( ProjectVersion ).filter_by(
				project_id=project_id,
				version=project_version,
			).first()

			# Delete previous version with same ID since we're updating it
			if previous_project_version != None:
				session.delete( previous_project_version )
				session.commit()
		
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
			project_id,
			project_config
		)
		
		self.write({
			"success": True,
			"project_id": project_id,
			"project_version": project_version
		})
		
def update_project_config( project_id, project_config ):
	# Convert to JSON if not already
	if type( project_config ) == dict:
		project_config = json.dumps(
			project_config
		)
	
	# Check to see if there's a previous project config
	previous_project_config = session.query( ProjectConfig ).filter_by(
		project_id=project_id
	).first()
	
	# If not, create one
	if previous_project_config == None:
		new_project_config = ProjectConfig()
		new_project_config.project_id = project_id
		new_project_config.config_json = project_config
		session.add( new_project_config )
	else: # Otherwise update the current config
		previous_project_config.project_id = project_id
		previous_project_config.config_json = project_config
	
	session.commit()
		
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
		
		for project_data in authenticated_user.projects:
			if self.json[ "query" ].lower() in str( project_data.name ).lower():
				project_search_results.append(
					project_data
				)
		
		results_list = []
		
		for project_search_result in project_search_results:
			project_item = {
				"id": project_search_result.id,
				"name": project_search_result.name,
				"timestamp": project_search_result.timestamp,
				"versions": []
			}
			
			for project_version in project_search_result.versions:
				project_item[ "versions" ].append(
					project_version.version
				)
				
			# Sort project versions highest to lowest
			project_item[ "versions" ].sort( reverse=True )
			
			results_list.append(
				project_item
			)
		
		self.write({
			"success": True,
			"results": results_list
		})
		
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
				"id": {
					"type": "string",
				},
				"version": {
					"type": "integer",
				}
			},
			"required": [
				"id",
				"version"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Retrieving saved project..." )

		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to access that project version!",
			})
			raise gen.Return()
			
		project = self.fetch_project()

		self.write({
			"success": True,
			"id": project.id,
			"version": project.version,
			"project_json": project.project_json
		})

	def fetch_project( self ):
		if 'version' not in self.json:
			return self.fetch_project_without_version(self.json[ "id" ])

		return self.fetch_project_by_version(self.json[ "id" ], self.json[ "version" ])

	def fetch_project_by_version( self, id, version ):
		project_version_result = session.query( ProjectVersion ).filter_by(
			project_id=id,
			version=version
		).first()

		return project_version_result

	def fetch_project_without_version( self, id ):
		project_version_result = session.query( ProjectVersion ).filter_by(
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
		
		logit( "Deleting saved project..." )
		
		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to delete that project!",
			})
			raise gen.Return()
			
		# Pull the latest project config
		project_config = session.query( ProjectConfig ).filter_by(
			project_id=self.json[ "id" ]
		).first()
		project_config_data = project_config.to_dict()
		project_config_dict = project_config_data[ "config_json" ]
		
		# Delete the API Gateway associated with this project
		if "api_gateway" in project_config_dict:
			api_gateway_id = project_config_dict[ "api_gateway" ][ "gateway_id" ]
			
			if api_gateway_id:
				logit( "Deleting associated API Gateway '" + api_gateway_id + "'..." )
				
				yield local_tasks.delete_rest_api(
					self.get_authenticated_user_cloud_configuration(),
					api_gateway_id
				)
		
		saved_project_result = session.query( Project ).filter_by(
			id=self.json[ "id" ]
		).first()
		
		session.delete( saved_project_result )
		session.commit()

		self.write({
			"success": True
		})
		
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
		
		deployment_data = yield deploy_diagram(
			self.get_authenticated_user_cloud_configuration(),
			project_name,
			project_id,
			diagram_data,
			project_config
		)
		
		# Check if the deployment failed
		if deployment_data[ "success" ] == False:
			logit( "We are now rolling back the deployments we've made...", "error" )
			yield teardown_infrastructure(
				self.get_authenticated_user_cloud_configuration(),
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
		
		existing_project = session.query( Project ).filter_by(
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
		
		session.commit()
		
		# Update project config
		logit( "Updating database with new project config..." )
		update_project_config(
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
		
		project_config = session.query( ProjectConfig ).filter_by(
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
		
		latest_deployment = session.query( Deployment ).filter_by(
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
		
		session.query( Deployment ).filter_by(
			project_id=self.json[ "project_id" ]
		).delete()
		
		session.commit()
		
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
	resources = yield local_tasks.get_resources(
		credentials,
		api_gateway_id
	)
	base_resource_id = resources[ 0 ][ "id" ]
	
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
	
	resources = yield local_tasks.get_resources(
		credentials,
		api_gateway_id
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
def get_project_id_execution_log_groups( credentials, project_id, max_results, continuation_token ):
	"""
	@project_id: The ID of the project deployed into production
	@max_results: The max number of timestamp groups you want to search
	for logs under. They are in 5 minute blocks so each result is AT LEAST
	(not at most) 5 minutes of logs.
	
	The result for this is the following format:
	
	results_dict = {
		"executions": {
			"execution_id": {
				"logs": [
					"full_s3_log_path"
				],
				"error": True, # If we find a log file with prefix of "EXCEPTION"
				"oldest_observed_timestamp": 1543785335,
			}
		},
		"continuation_token": "aASDWQ...",
	}
	"""
	results_dict = {}
	
	execution_log_timestamp_prefix_data = yield local_tasks.get_s3_pipeline_timestamp_prefixes(
		credentials,
		project_id,
		max_results,
		continuation_token
	)
	
	results_dict[ "continuation_token" ] = execution_log_timestamp_prefix_data[ "continuation_token" ]
	results_dict[ "executions" ] = {}
	
	execution_log_timestamp_prefixes = execution_log_timestamp_prefix_data[ "prefixes" ]
	
	timestamp_prefix_fetch_futures = []
	
	for execution_log_timestamp_prefix in execution_log_timestamp_prefixes:
		timestamp_prefix_fetch_futures.append(
			local_tasks.get_s3_pipeline_execution_ids(
				credentials,
				execution_log_timestamp_prefix,
				-1,
				False
			)
		)
		
	execution_id_prefixes_data = yield timestamp_prefix_fetch_futures
	
	# Flat list of prefixes
	execution_id_prefixes = []
	
	# Consolidate all data into just a final list of data
	for execution_id_prefix_data in execution_id_prefixes_data:
		execution_id_prefixes = execution_id_prefixes + execution_id_prefix_data[ "prefixes" ]
	
	# Now take all of the prefixes and get the full file paths under them
	s3_log_path_promises = []

	for execution_id_prefix in execution_id_prefixes:
		s3_log_path_promises.append(
			local_tasks.get_s3_pipeline_execution_logs(
				credentials,
				execution_id_prefix,
				-1
			)
		)
			
	s3_log_file_paths = yield s3_log_path_promises
	
	# Merge list of lists into just a list
	tmp_log_path_list = []
	for s3_log_file_path_array in s3_log_file_paths:
		for s3_log_file_path in s3_log_file_path_array:
			tmp_log_path_list.append(
				s3_log_file_path
			)
			
	s3_log_file_paths = tmp_log_path_list
	del tmp_log_path_list
	
	oldest_observed_timestamp = False
	
	for s3_log_file_path in s3_log_file_paths:
		path_parts = s3_log_file_path.split( "/" )
		execution_id = path_parts[ 2 ]
		log_file_name = path_parts[ 3 ]
		log_file_name_parts = log_file_name.split( "~" )
		log_type = log_file_name_parts[ 0 ]
		lambda_name = log_file_name_parts[ 1 ]
		log_id = log_file_name_parts[ 2 ]
		timestamp = int( log_file_name_parts[ 3 ] )
		
		# Initialize if it doesn't already exist
		if not ( execution_id in results_dict[ "executions" ] ):
			results_dict[ "executions" ][ execution_id ] = {
				"logs": [],
				"error": False,
				"oldest_observed_timestamp": timestamp
			}
			
		# Append the log path
		results_dict[ "executions" ][ execution_id ][ "logs" ].append(
			s3_log_file_path
		)
		
		# If the prefix is "EXCEPTION" we know we encountered an error
		if log_file_name.startswith( "EXCEPTION~" ):
			results_dict[ "executions" ][ execution_id ][ "error" ] = True
			
		# If the timestamp is older than the current, replace it
		if timestamp < results_dict[ "executions" ][ execution_id ][ "oldest_observed_timestamp" ]:
			results_dict[ "executions" ][ execution_id ][ "oldest_observed_timestamp" ] = timestamp
		
		# For the first timestamp
		if oldest_observed_timestamp == False:
			oldest_observed_timestamp = timestamp
			
		# If we've observed and older timestamp
		if timestamp < oldest_observed_timestamp:
			oldest_observed_timestamp = timestamp
	
	raise gen.Return( results_dict )
	
@gen.coroutine
def get_logs_data( credentials, log_paths_array ):
	"""
	Return data format is the following:
	{
		"lambda_name": []
	}
	"""
	s3_object_retrieval_futures = []
	for log_file_path in log_paths_array:
		s3_object_retrieval_futures.append(
			local_tasks.read_from_s3_and_return_input(
				credentials,
				credentials[ "logs_bucket" ],
				log_file_path
			)
		)
		
	s3_object_retrieval_data_results = yield s3_object_retrieval_futures
	
	return_data = {}
	
	for s3_object_retrieval_data in s3_object_retrieval_data_results:
		s3_path_parts = s3_object_retrieval_data[ "path" ].split( "/" )
		log_file_name = s3_path_parts[ 3 ]
		log_file_name_parts = log_file_name.split( "~" )
		log_type = log_file_name_parts[ 0 ]
		lambda_name = log_file_name_parts[ 1 ]
		log_id = log_file_name_parts[ 2 ]
		timestamp = int( log_file_name_parts[ 3 ] )
		log_data = json.loads(
			s3_object_retrieval_data[ "body" ]
		)
		
		if not ( log_data[ "function_name" ] in return_data ):
			return_data[ log_data[ "function_name" ] ] = []
			
		return_data[ log_data[ "function_name" ] ].append(
			log_data
		)
    
	# Reverse order for return values
	for key, value in return_data.iteritems():
		return_data[ key ] = return_data[ key ][::-1]
		
	raise gen.Return( return_data )

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
				"continuation_token": {
					"type": "string",
				}
			},
			"required": [
				"project_id"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Retrieving execution ID(s) and their metadata..." )
		
		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "project_id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to access that project's executions!",
			})
			raise gen.Return()
      
		continuation_token = False
		
		if "continuation_token" in self.json:
			continuation_token = self.json[ "continuation_token" ]
		
		execution_ids_metadata = yield get_project_id_execution_log_groups(
			self.get_authenticated_user_cloud_configuration(),
			self.json[ "project_id" ],
			100,
			continuation_token
		)
		
		self.write({
			"success": True,
			"result": execution_ids_metadata
		})
		
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
				"logs": {
					"type": "array",
				},
				
			},
			"required": [
				"logs"
			]
		}
		
		validate_schema( self.json, schema )
		
		logit( "Retrieving requested logs..." )
		
		logs_data = yield get_logs_data(
			self.get_authenticated_user_cloud_configuration(),
			self.json[ "logs" ],
		)
		
		self.write({
			"success": True,
			"result": logs_data
		})
		
@gen.coroutine
def delete_logs( credentials, project_id ):
	while True:
		log_paths = yield local_tasks.get_s3_pipeline_execution_logs(
			credentials,
			project_id + "/",
			1000
		)

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
		
		response = yield local_tasks.update_lambda_environment_variables(
			self.get_authenticated_user_cloud_configuration(),
			self.json[ "arn" ],
			self.json[ "environment_variables" ],
		)
		
		# Update the deployment diagram to reflect the new environment variables
		latest_deployment = session.query( Deployment ).filter_by(
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
		session.commit()
		
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
		
		log_output = yield local_tasks.get_lambda_cloudwatch_logs(
			self.get_authenticated_user_cloud_configuration(),
			self.json[ "arn" ]
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
		
@gen.coroutine
def strip_api_gateway( credentials, api_gateway_id ):
	"""
	Strip a given API Gateway of all of it's:
	* Resources
	* Resource Methods
	* Stages
	
	Allowing for the configuration details to be replaced.
	"""
	rest_resources = yield local_tasks.get_resources(
		credentials,
		api_gateway_id
	)
	
	# List of futures to finish before we continue
	deletion_futures = []
	
	# Iterate over resources and delete everything that
	# can be deleted.
	for resource_item in rest_resources:
		# We can't delete the root resource
		if resource_item[ "path" ] != "/":
			deletion_futures.append(
				local_tasks.delete_rest_api_resource(
					credentials,
					api_gateway_id,
					resource_item[ "id" ]
				)
			)
		
		# Delete the methods
		if "resourceMethods" in resource_item:
			for http_method, values in resource_item[ "resourceMethods" ].iteritems():
				deletion_futures.append(
					local_tasks.delete_rest_api_resource_method(
						credentials,
						api_gateway_id,
						resource_item[ "id" ],
						http_method
					)
				)
			
	rest_stages = yield local_tasks.get_stages(
		credentials,
		api_gateway_id
	)
	
	for rest_stage in rest_stages:
		deletion_futures.append(
			local_tasks.delete_stage(
				credentials,
				api_gateway_id,
				rest_stage[ "stageName" ]
			)
		)
	
	yield deletion_futures
	
	raise gen.Return( api_gateway_id )
	
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
				}
			},
			"required": [
				"organization_name",
				"name",
				"email"
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
				"code": "INVALID_EMAIL",
				"msg": str( e ) # The exception string is user-friendly by design.
			})
			raise gen.Return()
			
		# Create new organization for user
		new_organization = Organization()
		new_organization.name = self.json[ "organization_name" ]
		
		# Set defaults
		new_organization.payments_overdue = False
		
		# Check if the user is already registered
		user = session.query( User ).filter_by(
			email=self.json[ "email" ]
		).first()
		
		# If the user already exists, stop here and notify them.
		# They should be given the option to attempt to authenticate/confirm
		# their account by logging in.
		if user != None:
			self.write({
				"success": False,
				"code": "USER_ALREADY_EXISTS",
				"msg": "A user with that email address already exists!"
			})
			raise gen.Return()
		
		# Create the user itself and add it to the organization
		new_user = User()
		new_user.name = self.json[ "name" ]
		new_user.email = self.json[ "email" ]
		
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
		
		session.add( new_organization )
		session.commit()
		
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
		email_authentication_token = session.query( EmailAuthToken ).filter_by(
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
			session.commit()
			
			self.write( "That email token has expired, please try authenticating again to request a new one." )
			raise gen.Return()
		
		# Since the user has now authenticated
		# Mark the token as expired in the database
		email_authentication_token.is_expired = True
		
		# Pull the user's organization
		user_organization = session.query( Organization ).filter_by(
			id=email_authentication_token.user.organization_id
		).first()
		
		print( "User organization: " )
		print( user_organization )
		
		# Check if the user has previously authenticated via
		# their email address. If not we'll mark their email
		# as validated as well.
		if email_authentication_token.user.email_verified == False:
			email_authentication_token.user.email_verified = True
			
			# Check if there are reserved AWS accounts available
			aws_reserved_account = session.query( AWSAccount ).filter_by(
				is_reserved_account=True
			).first()
			
			# If one exists, add it to the account
			if aws_reserved_account != None:
				logit( "Adding a reserved AWS account to the newly registered Refinery account..." )
				aws_reserved_account.is_reserved_account = False
				aws_reserved_account.organization_id = user_organization.id
				session.commit()
				
				# Don't yield because we don't care about the result
				# Unfreeze/thaw the account so that it's ready for the new user
				# This takes ~30 seconds - worth noting. But that **should** be fine.
				local_tasks.unfreeze_aws_account(
					aws_reserved_account.to_dict()
				)
			
			# Additionally since they've validated their email we'll add them to Stripe
			customer_id = yield local_tasks.stripe_create_customer(
				email_authentication_token.user.email,
				email_authentication_token.user.name,
			)
			
			# Set user's payment_id to the Stripe customer ID
			email_authentication_token.user.payment_id = customer_id
		
		session.commit()
		
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
			self.write({
				"authenticated": True,
				"name": current_user.name,
				"email": current_user.email,
				"permission_level": current_user.permission_level,
				"trial_information": get_user_free_trial_information(
					self.get_authenticated_user()
				)
			})
			return
		
		self.write({
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
		user = session.query( User ).filter_by(
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
		
		session.commit()
		
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
		
		current_user = self.get_authenticated_user()
		credentials = self.get_authenticated_user_cloud_configuration()
		
		billing_data = yield local_tasks.get_sub_account_month_billing_data(
			credentials[ "account_id" ],
			self.json[ "billing_month" ],
			True
		)
		
		self.write( billing_data )
		
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
		date_info = get_current_month_start_and_end_date_strings()
		logit( "[ STATUS ] Generating invoices for " + date_info[ "month_start_date" ] + " -> " + date_info[ "next_month_first_day" ]  )
		yield local_tasks.generate_managed_accounts_invoices(
			date_info[ "month_start_date"],
			date_info[ "next_month_first_day" ],
		)
		logit( "[ STATUS ] Stripe billing job has completed!" )
		
class HealthHandler( BaseHandler ):
	@authenticated
	def get( self ):
		# Just run a dummy database query to ensure it's working
		session.query( User ).first()
		self.write({
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
	# Edge case for python2.7 because of the tight custom-runtime
	# integration which requires the redis library
	if language == "python2.7" and not ( "redis" in libraries ):
		libraries.append(
			"redis"
		)
	
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
		
		# Edge case for python2.7 because of the tight custom-runtime
		# integration which requires the redis library
		if self.json[ "language" ] == "python2.7" and not ( "redis" in self.json[ "libraries" ] ):
			self.json[ "libraries" ].append(
				"redis"
			)
		
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
		elif self.json[ "language" ] == "nodejs8.10":
			build_id = yield local_tasks.start_node810_codebuild(
				credentials,
				libraries_dict
			)
		elif self.json[ "language" ] == "php7.3":
			build_id = yield local_tasks.start_php73_codebuild(
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
		
		reserved_aws_pool_target_amount = int( os.environ.get( "reserved_aws_pool_target_amount" ) )
			
		current_aws_account_count = session.query( AWSAccount ).filter_by(
			is_reserved_account=True
		).count()
		
		logit( "Current AWS account(s) in pool is " + str( current_aws_account_count ) + " we have a target of " + str( reserved_aws_pool_target_amount ) )
		
		if current_aws_account_count < reserved_aws_pool_target_amount:
			logit( "We are under our target, creating new AWS account for the pool..." )
			local_tasks.provision_new_sub_aws_account()
		
def make_app( is_debug ):
	tornado_app_settings = {
		"debug": is_debug,
		"cookie_secret": os.environ.get( "cookie_secret_value" )
	}
	
	return tornado.web.Application([
		( r"/api/v1/health", HealthHandler ),
		( r"/authentication/email/([a-z0-9]+)", EmailLinkAuthentication ),
		( r"/api/v1/auth/me", GetAuthenticationStatus ),
		( r"/api/v1/auth/register", NewRegistration ),
		( r"/api/v1/auth/login", Authenticate ),
		( r"/api/v1/auth/logout", Logout ),
		( r"/api/v1/logs/executions/get", GetProjectExecutionLogs ),
		( r"/api/v1/logs/executions", GetProjectExecutions ),
		( r"/api/v1/aws/deploy_diagram", DeployDiagram ),
		( r"/api/v1/lambdas/create", SavedLambdaCreate ),
		( r"/api/v1/lambdas/search", SavedLambdaSearch ),
		( r"/api/v1/lambdas/delete", SavedLambdaDelete ),
		( r"/api/v1/lambdas/run", RunLambda ),
		( r"/api/v1/lambdas/logs", GetCloudWatchLogsForLambda ),
		( r"/api/v1/lambdas/env_vars/update", UpdateEnvironmentVariables ),
		( r"/api/v1/lambdas/build_libraries", BuildLibrariesPackage ),
		( r"/api/v1/lambdas/libraries_cache_check", CheckIfLibrariesCached ),
		( r"/api/v1/aws/run_tmp_lambda", RunTmpLambda ),
		( r"/api/v1/aws/infra_tear_down", InfraTearDown ),
		( r"/api/v1/aws/infra_collision_check", InfraCollisionCheck ),
		( r"/api/v1/projects/save", SaveProject ),
		( r"/api/v1/projects/search", SearchSavedProjects ),
		( r"/api/v1/projects/get", GetSavedProject ),
		( r"/api/v1/projects/delete", DeleteSavedProject ),
		( r"/api/v1/projects/config/get", GetProjectConfig ),
		( r"/api/v1/deployments/get_latest", GetLatestProjectDeployment ),
		( r"/api/v1/deployments/delete_all_in_project", DeleteDeploymentsInProject ),
		( r"/api/v1/billing/get_month_totals", GetBillingMonthTotals ),
		( r"/api/v1/billing/creditcards/add", AddCreditCardToken ),
		( r"/api/v1/billing/creditcards/list", ListCreditCards ),
		( r"/api/v1/billing/creditcards/delete", DeleteCreditCard ),
		( r"/api/v1/billing/creditcards/make_primary", MakeCreditCardPrimary ),
		# Temporarily disabled since it doesn't cache the CostExplorer results
		#( r"/api/v1/billing/forecast_for_date_range", GetBillingDateRangeForecast ),
		
		# These are "services" which are only called by external crons, etc.
		# External users are blocked from ever reaching these routes
		( r"/services/v1/maintain_aws_account_pool", MaintainAWSAccountReserves ),
		( r"/services/v1/billing_watchdog", RunBillingWatchdogJob ),
		( r"/services/v1/bill_customers", RunMonthlyStripeBillingJob )
	], **tornado_app_settings)

if __name__ == "__main__":
	logit( "Starting the Refinery service...", "info" )
	on_start()
	app = make_app(
		( os.environ.get( "is_debug" ).lower() == "true" )
	)
	server = tornado.httpserver.HTTPServer(
		app
	)
	server.bind(
		7777
	)
	Base.metadata.create_all( engine )
	
	if os.environ.get( "cf_enabled" ).lower() == "true":
		tornado.ioloop.IOLoop.current().run_sync( get_cloudflare_keys )
		
	server.start()
	tornado.ioloop.IOLoop.current().start()