#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
import tornado.escape
import tornado.ioloop
import tornado.web
import botocore
import subprocess
import traceback
import pystache
import logging
import hashlib
import random
import shutil
import base64
import string
import boto3
import uuid
import json
import yaml
import copy
import time
import jwt
import sys
import os
import io

from tornado import gen
from datetime import timedelta
from tornado.web import asynchronous
from botocore.exceptions import ClientError
from jsonschema import validate as validate_schema
from tornado.concurrent import run_on_executor, futures
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from email_validator import validate_email, EmailNotValidError

from models.initiate_database import *
from models.saved_function import SavedFunction
from models.saved_lambda import SavedLambda
from models.project_versions import ProjectVersion
from models.projects import Project
from models.organizations import Organization
from models.users import User
from models.email_auth_tokens import EmailAuthToken
from models.aws_accounts import AWSAccount
from models.deployments import Deployment
from models.project_config import ProjectConfig

from botocore.client import Config

logging.basicConfig(
	stream=sys.stdout,
	level=logging.INFO
)

import StringIO
import zipfile

from expiringdict import ExpiringDict
DEPENDENCY_CACHE = ExpiringDict(
	max_len=20,
	max_age_seconds=( 60 * 60 * 24 )
)

reload( sys )
sys.setdefaultencoding( "utf8" )

# Cloudflare Access public keys
CF_ACCESS_PUBLIC_KEYS = []
			
def on_start():
	global LAMDBA_BASE_CODES, LAMBDA_BASE_LIBRARIES, LAMBDA_SUPPORTED_LANGUAGES, CUSTOM_RUNTIME_CODE, CUSTOM_RUNTIME_LANGUAGES, EMAIL_TEMPLATES
	
	def inject_configurations( input_code ):
		return input_code.replace(
			"{{REDIS_PASSWORD_REPLACE_ME}}",
			os.environ.get( "lambda_redis_password" )
		).replace(
			"{{REDIS_HOSTNAME_REPLACE_ME}}",
			os.environ.get( "lambda_redis_hostname" )
		).replace(
			"\"{{REDIS_PORT_REPLACE_ME}}\"",
			os.environ.get( "lambda_redis_port" )
		).replace(
			"{{LOG_BUCKET_NAME_REPLACE_ME}}",
			os.environ.get( "pipeline_logs_bucket" )
		)
	
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
	]
	
	LAMBDA_BASE_LIBRARIES = {
		"python2.7": [
			"redis",
		],
		"nodejs8.10": [],
	}
	
	LAMBDA_SUPPORTED_LANGUAGES = [
		"python2.7",
		"nodejs8.10",
	]
	
	CUSTOM_RUNTIME_CODE = ""
	
	with open( "./custom-runtime/base-src/bootstrap", "r" ) as file_handler:
		CUSTOM_RUNTIME_CODE = inject_configurations(
			file_handler.read()
		)

	for language_name, libraries in LAMBDA_BASE_LIBRARIES.iteritems():
		# Load Lambda base templates
		with open( "./lambda_bases/" + language_name, "r" ) as file_handler:
			LAMDBA_BASE_CODES[ language_name ] = inject_configurations(
				file_handler.read()
			)

# This is purely for sending emails as part of Refinery's
# regular operations (e.g. authentication via email code, etc).
SES_EMAIL_CLIENT = boto3.client(
	"ses",
	aws_access_key_id=os.environ.get( "ses_emails_access_key" ),
	aws_secret_access_key=os.environ.get( "ses_emails_secret_key" ),
	region_name=os.environ.get( "ses_emails_region" )
)

def get_aws_client( client_type, credentials ):
	"""
	Take an AWS client type ("s3", "lambda", etc) and an AWS
	credentials dict and return an AWS client object.
	"""
	
	client_options = {
		"aws_access_key_id": credentials[ "access_key" ],
		"aws_secret_access_key": credentials[ "secret_key" ],
		"region_name": credentials[ "region" ],
	}
	
	if client_type == "lambda":
		client_options[ "config" ] = Config(
			connect_timeout=50,
			read_timeout=( 60 * 15 )
		)
	elif client_type == "s3":
		client_options[ "config" ] = Config(
			max_pool_connections=( 1000 * 2 )
		)
		
	return boto3.client(
		client_type,
		**client_options
	)

def pprint( input_dict ):
	try:
		print( json.dumps( input_dict, sort_keys=True, indent=4, separators=( ",", ": " ) ) )
	except:
		print( input_dict )
		
def logit( message, message_type="info" ):
	if message_type == "info":
		logging.info( message )
	elif message_type == "warn":
		logging.warn( message )
	elif message_type == "debug":
		logging.debug( message )
	else:
		logging.info( message )
	
class BaseHandler( tornado.web.RequestHandler ):
	def __init__( self, *args, **kwargs ):
		super( BaseHandler, self ).__init__( *args, **kwargs )
		self.set_header( "Access-Control-Allow-Origin", os.environ.get( "access_control_allow_origin" ), )
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
		
	def is_owner_of_saved_function( self, saved_function_id ):
		saved_function = session.query( SavedFunction ).filter_by(
			id=saved_function_id
		).first()
		
		return ( saved_function.user_id == self.get_authenticated_user_id() )
		
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

	def logit( self, message, message_type="info" ):
		message = "[" + self.request.remote_ip + "] " + message
		
		logit( message )
		
	def prepare( self ):
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
				raise gen.Return()
				
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
				print( "Cloudflare Access verification check failed." )
				self.error(
					"Error, Cloudflare Access verification check failed.",
					"CF_ACCESS_DENIED"
				)
				raise gen.Return()
		
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
		self.logit(
			error_message,
			message_type="warn"
		)
		
		self.write(json.dumps({
			"success": False,
			"msg": error_message,
			"id": error_id
		}))
		
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
		"msg": "User must be authenticated to hit this endpoint",
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
	
class TaskSpawner(object):
		def __init__(self, loop=None):
			self.executor = futures.ThreadPoolExecutor( 60 )
			self.loop = loop or tornado.ioloop.IOLoop.current()
			
		@run_on_executor
		def send_registration_confirmation_email( self, email_address, auth_token ):
			registration_confirmation_link = os.environ.get( "access_control_allow_origin" ) + "/authentication/email/" + auth_token
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
			authentication_link = os.environ.get( "access_control_allow_origin" ) + "/authentication/email/" + auth_token
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
			
		@run_on_executor
		def deploy_aws_lambda( self, credentials, func_name, language, description, role_name, zip_data, timeout, memory, vpc_config, environment_variables, tags_dict, layers ):
			return TaskSpawner._deploy_aws_lambda( credentials, func_name, language, description, role_name, zip_data, timeout, memory, vpc_config, environment_variables, tags_dict, layers )

		@staticmethod
		def _deploy_aws_lambda( credentials, func_name, language, description, role_name, zip_data, timeout, memory, vpc_config, environment_variables, tags_dict, layers ):
			if language in CUSTOM_RUNTIME_LANGUAGES:
				language = "provided"

			"""
			First upload the data to S3 at {{zip_sha1}}.zip
			
			We then can check if there's an existing cached copy
			that we can use before we upload it ourself.
			
			TODO: Improve this method, generated zips basically never have matching sigs.
			"""
			# Generate SHA256 hash of package
			hash_key = hashlib.sha256(
				zip_data
			).hexdigest()
			s3_package_zip_path = hash_key + ".zip"
			
			# First check if it already exists
			already_exists = False
			
			# Create S3 client
			s3_client = get_aws_client(
				"s3",
				credentials
			)
			
			# S3 head response
			try:
				s3_head_response = s3_client.head_object(
					Bucket=credentials[ "lambda_packages_bucket" ],
					Key=s3_package_zip_path
				)
				
				# If we didn't encounter a not-found exception, it exists.
				already_exists = True
			except ClientError as e:
				pass
			
			if not already_exists:
				print( "Doesn't already exist in S3 cache, writing to S3..." )
				response = s3_client.put_object(
					Key=s3_package_zip_path,
					Bucket=credentials[ "lambda_packages_bucket" ],
					Body=zip_data,
				)
				
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
				print( "Exception occured: " )
				pprint( e )
				if e.response[ "Error" ][ "Code" ] == "ResourceConflictException":
					print( "Duplicate! Deleting previous to replace it..." )
					
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
						zip_data,
						timeout,
						memory,
						vpc_config,
						environment_variables,
						tags_dict,
						layers
					)
				else:
					return False
			
			return response
			
		@staticmethod
		def get_python27_lambda_base_zip( libraries ):
			# Check if we have a cache .zip ready to go
			libraries.sort()
			hash_key = hashlib.sha256(
				"python2.7" + json.dumps(
					libraries
				)
			).hexdigest()
			
			# If we have it, return it for use
			if hash_key in DEPENDENCY_CACHE:
				return_zip = DEPENDENCY_CACHE[ hash_key ][:]
				return return_zip

			build_directory = "/tmp/" + str( uuid.uuid4() ) + "/"
			build_directory_env = build_directory + "env/"
			build_directory_requirements_txt = build_directory + "requirements.txt"

			# Create directory to build lambda in
			os.mkdir(
				build_directory
			)
			
			# virtualenv
			os.mkdir(
				build_directory_env
			)
			
			# Create virtualenv
			try:
				virtualenv_process = subprocess.check_output(
					[
						"/usr/bin/virtualenv",
						build_directory_env
					]
				)
			except subprocess.CalledProcessError, e:
				print( "Exception occured while creating virtualenv: " )
				print( e.output )
				
			# Write requirements.txt
			with open( build_directory_requirements_txt, "w" ) as file_handler:
				file_handler.write(
					"\n".join(
						libraries
					)
				)
				
			# Using virtualenv pip, install packages
			try:
				virtualenv_process = subprocess.check_output(
					[
						build_directory_env + "bin/pip",
						"install",
						"-r",
						build_directory_requirements_txt
					]
				)
			except subprocess.CalledProcessError, e:
				print( "Exception occured while installing dependencies: " )
				print( e.output )
				
			# Create .zip file
			zip_directory = "/tmp/" + str( uuid.uuid4() ) + "/"
			
			# Zip filename
			zip_filename = "/tmp/" + str( uuid.uuid4() ) + ".zip"
			
			# zip dir
			os.mkdir(
				zip_directory
			)
			
			copy_command = "/bin/cp -r " + build_directory + "/env/lib/python2.7/site-packages/* " + zip_directory
			
			cp_process = subprocess.Popen(
				copy_command,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE
			)
			stdout, stderr = cp_process.communicate()
				
			# Clean up original directory
			shutil.rmtree( build_directory )
			
			# Create .zip file
			zip_command = "/usr/bin/zip -r " + zip_filename + " *"
			
			zip_process = subprocess.Popen(
				zip_command,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				cwd=zip_directory
			)
			stdout, stderr = zip_process.communicate()
			
			# Clean up zip directory
			shutil.rmtree( zip_directory )
			
			# Zip bytes
			zip_data = False
			
			# Read zip bytes from disk
			with open( zip_filename, "rb" ) as file_handler:
				zip_data = file_handler.read()

			# Delete zip file now that we've read it
			os.remove( zip_filename )
			
			# Cache this result in memory for future use
			DEPENDENCY_CACHE[ hash_key ] = zip_data
			
			# Copy the cache data and return it
			return_zip = DEPENDENCY_CACHE[ hash_key ][:]
			
			return return_zip
			
		@staticmethod
		def get_nodejs_810_base_zip( libraries ):
			# Check if we have a cache .zip ready to go
			libraries.sort()
			hash_key = hashlib.sha256(
				"nodejs8.10" + json.dumps(
					libraries
				)
			).hexdigest()
			
			# If we have it, return it for use
			if hash_key in DEPENDENCY_CACHE:
				return_zip = DEPENDENCY_CACHE[ hash_key ][:]
				return return_zip
				
			package_json_template = {
				"name": "refinery-lambda",
				"version": "1.0.0",
				"description": "Lambda created by Refinery",
				"main": "main.js",
				"dependencies": {},
				"devDependencies": {},
				"scripts": {
					"test": "echo \"Error: no test specified\" && exit 1",
					"start": "node server.js"
				}
			}
			
			# TODO if no dependencies then just ignore this part

			# Set up dependencies
			for library in libraries:
				if " " in library:
					library_parts = library.split( " " )
					package_json_template[ "dependencies" ][ library_parts[0] ] = library_parts[1]
				else:
					package_json_template[ "dependencies" ][ library ] = "*"

			build_directory = "/tmp/" + str( uuid.uuid4() ) + "/"
			build_directory_package_json_path = build_directory + "package.json"
			
			# Create directory to build lambda in
			os.mkdir(
				build_directory
			)
			
			# Write package.json
			with open( build_directory_package_json_path, "w" ) as file_handler:
				file_handler.write(
					json.dumps(
						package_json_template,
						False,
						4
					)
				)
			
			if len( libraries ) > 0:
				# Use npm to create node_modules from package.json
				npm_process = subprocess.Popen(
					"/usr/bin/npm install",
					shell=True,
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					cwd=build_directory
				)
				stdout, stderr = npm_process.communicate()
			
			# This files location
			source_file_directory = os.path.dirname(os.path.realpath(__file__))
			
			# Copy custom runtime files over
			cp_runtime_command = "/bin/cp -r * " + build_directory + " && cp " + source_file_directory + "/custom-runtime/node8.10/runtime " + build_directory + " && rm " + build_directory + "bootstrap"
			
			# Copy files
			copy_process = subprocess.Popen(
				cp_runtime_command,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				cwd=source_file_directory + "/custom-runtime/base-src/"
			)
			stdout, stderr = copy_process.communicate()
			
			# Zip filename
			zip_filename = "/tmp/" + str( uuid.uuid4() ) + ".zip"
			
			# Create .zip file
			zip_command = "/usr/bin/zip -r " + zip_filename + " *"
			
			zip_process = subprocess.Popen(
				zip_command,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				cwd=build_directory
			)
			stdout, stderr = zip_process.communicate()
			
			# Clean up build directory
			shutil.rmtree( build_directory )
			
			# Zip bytes
			zip_data = False
			
			# Read zip bytes from disk
			with open( zip_filename, "rb" ) as file_handler:
				zip_data = file_handler.read()

			# Delete zip file now that we've read it
			os.remove( zip_filename )
			
			# Cache this result in memory for future use
			DEPENDENCY_CACHE[ hash_key ] = zip_data
			
			# Copy the cache data and return it
			return_zip = DEPENDENCY_CACHE[ hash_key ][:]
			
			return return_zip
			
		@staticmethod
		def _build_nodejs_810_lambda( code, libraries, transitions, execution_mode, execution_pipeline_id, execution_log_level ):
			"""
			Customize and inject custom runtime.
			"""
			bootstrap_content = CUSTOM_RUNTIME_CODE
			bootstrap_content = TaskSpawner._get_custom_python_base_code(
				bootstrap_content,
				libraries,
				transitions,
				execution_mode,
				execution_pipeline_id,
				execution_log_level
			)
			
			"""
			Inject base libraries (e.g. redis) into lambda
			and the init code.
			"""
			
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "nodejs8.10" ]
			
			# Append required libraries if not already required
			for init_library in LAMBDA_BASE_LIBRARIES[ "nodejs8.10" ]:
				if not init_library in libraries:
					libraries.append(
						init_library
					)
			
			base_zip_data = TaskSpawner.get_nodejs_810_base_zip(
				libraries
			)
			
			tmp_zip_file = "/tmp/" + str( uuid.uuid4() ) + ".zip"
			
			with open( tmp_zip_file, "w" ) as file_handler:
				file_handler.write(
					base_zip_data
				)
				
			with zipfile.ZipFile( tmp_zip_file, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
				info = zipfile.ZipInfo(
					"lambda"
				)
				info.external_attr = 0777 << 16L
				
				# Write lambda.py into new .zip
				zip_file_handler.writestr(
					info,
					code
				)
				
				# Write bootstrap into new .zip
				bootstrap_info = zipfile.ZipInfo(
					"bootstrap"
				)
				bootstrap_info.external_attr = 0777 << 16L
				
				# Write lambda.py into new .zip
				zip_file_handler.writestr(
					bootstrap_info,
					bootstrap_content
				)
				
			with open( tmp_zip_file, "rb" ) as file_handler:
				zip_data = file_handler.read()
			
			# Delete zip file now that we've read it
			os.remove( tmp_zip_file )
			
			return zip_data

		@run_on_executor
		def build_lambda( self, language, code, libraries, transitions, execution_mode, execution_pipeline_id, execution_log_level ):
			if not ( language in LAMBDA_SUPPORTED_LANGUAGES ):
				raise Exception( "Error, this language '" + language + "' is not yet supported by refinery!" )
			
			if language == "python2.7":
				return TaskSpawner._build_python_lambda( code, libraries, transitions, execution_mode, execution_pipeline_id, execution_log_level )
			elif language == "nodejs8.10":
				return TaskSpawner._build_nodejs_810_lambda( code, libraries, transitions, execution_mode, execution_pipeline_id, execution_log_level )
				
		@staticmethod
		def _get_custom_python_base_code( code, libraries, transitions, execution_mode, execution_pipeline_id, execution_log_level ):
			# Convert tabs to four spaces
			code = code.replace( "\t", "	" )
			
			code = code.replace( "\"{{TRANSITION_DATA_REPLACE_ME}}\"", json.dumps( json.dumps( transitions ) ) )
			code = code.replace( "{{AWS_REGION_REPLACE_ME}}", os.environ.get( "region_name" ) )
			code = code.replace( "{{SPECIAL_EXECUTION_MODE}}", execution_mode )
			
			if execution_pipeline_id:
				code = code.replace( "{{EXECUTION_PIPELINE_ID_REPLACE_ME}}", execution_pipeline_id )
				code = code.replace( "{{PIPELINE_LOGGING_LEVEL_REPLACE_ME}}", execution_log_level )
			else:
				code = code.replace( "{{EXECUTION_PIPELINE_ID_REPLACE_ME}}", "" )
				code = code.replace( "{{PIPELINE_LOGGING_LEVEL_REPLACE_ME}}", "LOG_NONE" )
			
			return code
		
		@staticmethod
		def _build_python_lambda( code, libraries, transitions, execution_mode, execution_pipeline_id, execution_log_level ):
			"""
			Build Lambda package zip and return zip data
			"""
			
			"""
			Inject base libraries (e.g. redis) into lambda
			and the init code.
			"""

			# Get customized base code
			code = code + "\n\n" + LAMDBA_BASE_CODES[ "python2.7" ]
			code = TaskSpawner._get_custom_python_base_code(
				code,
				libraries,
				transitions,
				execution_mode,
				execution_pipeline_id,
				execution_log_level
			)
			
			for init_library in LAMBDA_BASE_LIBRARIES[ "python2.7" ]:
				if not init_library in libraries:
					libraries.append(
						init_library
					)
			
			base_zip_data = TaskSpawner.get_python27_lambda_base_zip(
				libraries
			)
			
			tmp_zip_file = "/tmp/" + str( uuid.uuid4() ) + ".zip"
			
			with open( tmp_zip_file, "w" ) as file_handler:
				file_handler.write(
					base_zip_data
				)
				
			with zipfile.ZipFile( tmp_zip_file, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
				info = zipfile.ZipInfo(
					"lambda.py"
				)
				info.external_attr = 0777 << 16L
				
				# Write lambda.py into new .zip
				zip_file_handler.writestr(
					info,
					code.encode( "utf-8" )
				)
				
			with open( tmp_zip_file, "rb" ) as file_handler:
				zip_data = file_handler.read()
			
			# Delete zip file now that we've read it
			os.remove( tmp_zip_file )
			
			return zip_data
			
		@run_on_executor
		def create_cloudwatch_rule( self, credentials, id, name, schedule_expression, description, input_dict ):
			events_client = get_aws_client(
				"events",
				credentials,
			)
			
			# Events role ARN is able to be generated off of the account ID
			# The role name should be the same for all accounts.
			# arn:aws:iam::148731734429:role/refinery_aws_cloudwatch_admin_role
			events_role_arn = "arn:aws:iam::" + str( credentials[ "account_id" ] ) + ":role/refinery_aws_cloudwatch_admin_role"
			
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
			
			targets_data = 	{
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
					print( "SQS queue was deleted too recently, trying again in ten seconds..." )
					
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
				print( "[ STATUS ] Grabbing log events from '" + log_group_name + "' at '" + stream_id + "'..." )
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
				print( "Exception occurred while deleting method '" + method + "'!" )
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
			
			print( "Deployment response: " )
			pprint( deployment_response )
			
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
			
			print( "Create REST API resource response: " )
			pprint( response )
			
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
			
			print( "Cleaning up IAM policies from no-longer-existing API Gateways attached to Lambda..." )
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
					print( "API Gateway ID: " + api_gateway_id )
					
					api_gateway_data = api_gateway_client.get_rest_api(
						restApiId=api_gateway_id,
					)
				except:
					
					print( "API Gateway does not exist, deleting IAM policy..." )
					
					delete_permission_response = lambda_client.remove_permission(
						FunctionName=lambda_name,
						StatementId=statement[ "Sid" ]
					)
					
					print( "Delete permission response: " )
					pprint( delete_permission_response )
			
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
			
			print( "Source ARN: " )
			print( source_arn )
			
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
		
		self.logit( "Running Lambda with ARN of '" + self.json[ "arn" ] + "'..." )
		
		# Try to parse Lambda input as JSON
		try:
			self.json[ "input_data" ] = json.loads(
				self.json[ "input_data" ]
			)
		except:
			pass
		
		self.logit( "Executing Lambda..." )
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
		
		self.logit( "Building Lambda package..." )

		lambda_zip_package_data = yield local_tasks.build_lambda(
			self.json[ "language" ],
			self.json[ "code" ],
			self.json[ "libraries" ],
			{
				"then": [],
				"else": [],
				"exception": [],
				"if": [],
				"fan-out": [],
				"fan-in": [],
			},
			"REGULAR",
			False,
			False
		)
		
		random_node_id = get_random_node_id()
		
		credentials = self.get_authenticated_user_cloud_configuration()
		
		lambda_role = "arn:aws:iam::" + str( credentials[ "account_id" ] ) + ":role/refinery_aws_lambda_admin_role"
		
		self.logit( "Deploying Lambda to S3..." )
		deployed_lambda_data = yield local_tasks.deploy_aws_lambda(
			credentials,
			random_node_id,
			self.json[ "language" ],
			"AWS Lambda being inline tested.",
			lambda_role,
			lambda_zip_package_data,
			self.json[ "max_execution_time" ], # Max AWS execution time
			self.json[ "memory" ], # MB of execution memory
			{}, # VPC data
			self.json[ "environment_variables" ], # Env list
			{
				"project": "None"
			},
			self.json[ "layers" ]
		)
		
		# Try to parse Lambda input as JSON
		try:
			self.json[ "input_data" ] = json.loads(
				self.json[ "input_data" ]
			)
		except:
			pass
		
		self.logit( "Executing Lambda..." )
		lambda_result = yield local_tasks.execute_aws_lambda(
			self.get_authenticated_user_cloud_configuration(),
			deployed_lambda_data[ "FunctionArn" ],
			{
				"_refinery": {
					"throw_exceptions_fully": True,
					"input_data": self.json[ "input_data" ]
				}
			},
		)

		self.logit( "Deleting Lambda..." )
		
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
		
def refinery_to_aws_step_function( refinery_dict, name_to_arn_map ):
	"""
	Generates an AWS step function structure out of a refinery structure
	"""
	return_step_function_data = {
		"Comment": "Step Function generated by refinery"
	}
	
	states_dict = {}
	
	special_nodes = [
		"start_node",
		"end_node"
	]
	
	# Generate ID -> Name map
	id_to_name_map = {}
	name_to_id_map = {}
	for workflow_state in refinery_dict[ "workflow_states" ]:
		id_to_name_map[ workflow_state[ "id" ] ] = workflow_state[ "name" ]
		name_to_id_map[ workflow_state[ "name" ] ] = get_lambda_safe_name(
			workflow_state[ "id" ]
		)
	
	first_node = False
	end_nodes = []
	
	# Determine start and end nodes
	for workflow_relationship in refinery_dict[ "workflow_relationships" ]:
		if workflow_relationship[ "node" ] == "start_node":
			first_node = workflow_relationship[ "next" ]
			
		if workflow_relationship[ "next" ] == "end_node":
			end_nodes.append(
				workflow_relationship[ "node" ]
			)
			
	for workflow_state in refinery_dict[ "workflow_states" ]:
		# Ignore special states like start_node
		if not workflow_state[ "id" ] in special_nodes:
			next_node = False
			# Look for relationships incase of next node
			for workflow_relationship in refinery_dict[ "workflow_relationships" ]:
				if not workflow_relationship[ "next" ] in special_nodes:
					if workflow_relationship[ "node" ] == workflow_state[ "id" ]:
						next_node = get_lambda_safe_name(
							id_to_name_map[ workflow_relationship[ "next" ] ]
						)
			
			aws_state_dict = {
				"Type": "Task",
				"Resource": name_to_arn_map[ get_lambda_safe_name( workflow_state[ "name" ] ) ],
			}
			
			# If it's the first node, set StartAt
			if workflow_state[ "id" ] == first_node:
				return_step_function_data[ "StartAt" ] = get_lambda_safe_name( workflow_state[ "name" ] )
				
			# If it's the last node set "End"
			if workflow_state[ "id" ] in end_nodes:
				aws_state_dict[ "End" ] = True
				
			if next_node:
				aws_state_dict[ "Next" ] = next_node
			
			states_dict[ get_lambda_safe_name( workflow_state[ "name" ] ) ] = aws_state_dict
			
	return_step_function_data[ "States" ] = states_dict
			
	return return_step_function_data
	
class SavedFunctionSearch( BaseHandler ):
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
		
		self.logit(
			"Searching saved functions..."
		)
		
		# Get user's saved functions and search through them
		saved_functions = session.query( SavedFunction ).filter_by(
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
			for saved_function in saved_functions:
				if self.json[ "query" ].lower() in getattr( saved_function, searchable_attribute ).lower() and not ( saved_function.id in existing_ids ):
					# Add to results
					results_list.append(
						saved_function.to_dict()
					)
					
					# Add to existing IDs so we don't have duplicates
					existing_ids.append(
						saved_function.id
					)
				
		self.write({
			"success": True,
			"results": results_list
		})
		
class SavedFunctionCreate( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Create a function to save for later use.
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
				}
			},
			"required": [
				"name",
				"description",
				"code",
				"language",
				"libraries"
			]
		}
		
		validate_schema( self.json, schema )
		
		self.logit(
			"Saving function data..."
		)
		
		new_function = SavedFunction()
		new_function.name = self.json[ "name" ]
		new_function.description = self.json[ "description" ]
		new_function.code = self.json[ "code" ]
		new_function.language = self.json[ "language" ]
		new_function.libraries = json.dumps(
			self.json[ "libraries" ]
		)
		new_function.user_id = self.get_authenticated_user_id()
		
		session.add( new_function )
		session.commit()
		
		self.write({
			"success": True,
			"id": new_function.id
		})
		
class SavedFunctionUpdate( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Update a saved function
		"""
		schema = {
			"type": "object",
			"properties": {
				"id": {
					"type": "string",
				},
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
				}
			},
			"required": [
				"id",
				"name",
				"description",
				"code",
				"language",
				"libraries"
			]
		}
		
		validate_schema( self.json, schema )
		
		self.logit(
			"Updating function data..."
		)
		
		if not self.is_owner_of_saved_function( self.json[ "id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to access that saved function!",
			})
			raise gen.Return()
		
		saved_function = session.query( SavedFunction ).filter_by(
			id=self.json[ "id" ]
		).first()
		
		saved_function.name = self.json[ "name" ]
		saved_function.description = self.json[ "description" ]
		saved_function.code = self.json[ "code" ]
		saved_function.language = self.json[ "language" ]
		saved_function.libraries = json.dumps(
			self.json[ "libraries" ]
		)
		session.commit()
		
		self.write({
			"success": True,
			"id": saved_function.id
		})
		
class SavedFunctionDelete( BaseHandler ):
	@authenticated
	@gen.coroutine
	def delete( self ):
		"""
		Delete a saved function
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
		
		self.logit(
			"Deleting saved function data..."
		)
		
		if not self.is_owner_of_saved_function( self.json[ "id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to delete that saved function!",
			})
			raise gen.Return()
		
		session.query( SavedFunction ).filter_by(
			id=self.json[ "id" ]
		).delete()
		
		session.commit()
		
		self.write({
			"success": True
		})
		
@gen.coroutine
def deploy_lambda( credentials, id, name, language, code, libraries, max_execution_time, memory, transitions, execution_mode, execution_pipeline_id, execution_log_level, environment_variables, layers ):
	logit(
		"Building '" + name + "' Lambda package..."
	)
	
	lambda_zip_package_data = yield local_tasks.build_lambda(
		language,
		code,
		libraries,
		transitions,
		execution_mode,
		execution_pipeline_id,
		execution_log_level
	)
	
	logit(
		"Deploying '" + name + "' Lambda package to production..."
	)
	
	lambda_role = "arn:aws:iam::" + str( credentials[ "account_id" ] ) + ":role/refinery_aws_lambda_admin_role"

	deployed_lambda_data = yield local_tasks.deploy_aws_lambda(
		credentials,
		name,
		language,
		"AWS Lambda deployed via refinery",
		lambda_role,
		lambda_zip_package_data,
		max_execution_time, # Max AWS execution time
		memory, # MB of execution memory
		{}, # VPC data
		environment_variables,
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
			
	print( "Teardown node list: " )
	pprint( teardown_nodes_list )
		
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
				128,
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
			
			print( "[ STATUS ] Deployed node '" + deploy_future_data[ "name" ] + "' successfully!" )
			
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
			print( "[ ERROR ] Failed to deploy node '" + deploy_future_data[ "name" ] + "'!" )
			print( "The full exception details can be seen below: " )
			traceback.print_exc()
			deployment_exceptions.append({
				"id": deploy_future_data[ "id" ],
				"name": deploy_future_data[ "name" ],
				"type": deploy_future_data[ "type" ],
				"exception": traceback.format_exc()
			})
	
	# This is the earliest point we can apply the breaks in the case of an exception
	# It's the callers responsibility to tear down the nodes
	if len( deployment_exceptions ) > 0:
		print( "[ ERROR ] An uncaught exception occurred during the deployment process!" )
		pprint( deployment_exceptions )
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
		
		print( "Deploy stage results: " )
		pprint( deploy_stage_results )
	
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
	
	print( "Diagram: " )
	pprint( diagram_data )
	
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
		
		self.logit(
			"Saving Lambda data..."
		)
		
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
		
		self.logit(
			"Searching saved Lambdas..."
		)
		
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
		
		self.logit(
			"Deleting Lambda data..."
		)
		
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
		
		print( "Teardown results: ")
		pprint( teardown_operation_results )
		
		self.write({
			"success": True,
			"result": teardown_operation_results
		})
	
class InfraCollisionCheck( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		self.logit(
			"Checking for production collisions..."
		)
		
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
		
		print( "Collision check results: " )
		pprint( collision_check_results )
		
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
		self.logit(
			"Saving project to database..."
		)
		
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
		
		self.logit(
			"Searching saved projects..."
		)
		
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
		
		self.logit(
			"Retrieving saved project..."
		)

		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have priveleges to access that project version!",
			})
			raise gen.Return()
			
		project_version_result = session.query( ProjectVersion ).filter_by(
			project_id=self.json[ "id" ],
			version=self.json[ "version" ]
		).first()
		
		self.write({
			"success": True,
			"project_json": project_version_result.project_json
		})
		
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
		
		self.logit(
			"Deleting saved project..."
		)
		
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
		
@gen.coroutine
def warm_lambda_base_caches():
	"""
	Kicks off building the dependency .zip templates for the base
	builds so that future builds will be cached and will execute faster.
	"""
	
	lambda_build_futures = []
	
	for supported_language in LAMBDA_SUPPORTED_LANGUAGES:
		lambda_build_futures.append(
			local_tasks.build_lambda(
				supported_language,
				"",
				[],
				{
					"then": [],
					"else": [],
					"exception": [],
					"if": [],
					"fan-out": [],
					"fan-in": [],
				},
				"REGULAR",
				False,
				False
			)
		)
		
	results = yield lambda_build_futures
	
	print( "Lambda base-cache has been warmed!" )
		
class DeployDiagram( BaseHandler ):
	@authenticated
	@gen.coroutine
	def post( self ):
		# TODO: Add jsonschema
		
		self.logit(
			"Deploying diagram to production..."
		)
		
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
			print( "[ ERROR ] We are now rolling back the deployments we've made..." )
			yield teardown_infrastructure(
				self.get_authenticated_user_cloud_configuration(),
				deployment_data[ "teardown_nodes_list" ]
			)
			print( "[ ERROR ] We've completed our rollback, returning an error..." )
			
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
		
		self.logit(
			"Retrieving project deployments..."
		)
		
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
		
		self.logit(
			"Retrieving project deployments..."
		)
		
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
		
		self.logit(
			"Deleting deployments from database..."
		)
		
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
			print( "Creating section '" + path_part + "'..." )
			new_resource = yield local_tasks.create_resource(
				credentials,
				api_gateway_id,
				current_base_pointer_id,
				path_part
			)
			
			current_base_pointer_id = new_resource[ "id" ]
	
	print( "Creating HTTP method..." )
	
	# Create method on base resource
	method_response = yield local_tasks.create_method(
		credentials,
		"HTTP Method",
		api_gateway_id,
		current_base_pointer_id,
		http_method,
		False,
	)
	
	print( "HTTP method response: " )
	pprint( method_response )
	
	print( "Linking Lambda to endpoint..." )
	
	# Link the API Gateway to the lambda
	link_response = yield local_tasks.link_api_method_to_lambda(
		credentials,
		api_gateway_id,
		current_base_pointer_id,
		http_method, # GET was previous here
		route,
		lambda_name
	)
	
	print( "Lambda link response: " )
	pprint(
		link_response
	)
	
	print( "All resources now that we've added some: " )
	resources = yield local_tasks.get_resources(
		credentials,
		api_gateway_id
	)
	pprint(
		resources
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
	
	print( "Requesting Cloudflare's Access keys for '" + os.environ.get( "cf_certs_url" ) + "'..." )
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
	
	print( "Private keys to be updated again in " + str( public_keys_update_interval ) + " second(s)..." )
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
		print( "Retrieving execution id(s) under " + execution_log_timestamp_prefix + "..." )
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
		print( "Retrieving log paths under " + execution_id_prefix + "..." )
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
		
		self.logit(
			"Retrieving execution ID(s) and their metadata..."
		)
		
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
		
		self.logit(
			"Retrieving requested logs..."
		)
		
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
		print( "Collecting objects to delete..." )
		log_paths = yield local_tasks.get_s3_pipeline_execution_logs(
			credentials,
			project_id + "/",
			1000
		)

		print( "Got back " + str( len( log_paths ) ) + " log object(s)!" )
		
		if len( log_paths ) == 0:
			break
		
		print( "Deleting objects..." )
		yield local_tasks.bulk_s3_delete(
			credentials,
			credentials[ "logs_bucket" ],
			log_paths
		)
		print( "Objects deleted!" )
		
class UpdateEnvironmentVariables( BaseHandler ):
	@authenticated
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
		
		self.logit(
			"Updating environment variables..."
		)
		
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
		
		self.logit(
			"Retrieving CloudWatch logs..."
		)
		
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
	
	pprint(
		rest_resources
	)
	
	# List of futures to finish before we continue
	deletion_futures = []
	
	# Iterate over resources and delete everything that
	# can be deleted.
	for resource_item in rest_resources:
		# We can't delete the root resource
		if resource_item[ "path" ] != "/":
			print( "Deleting resource ID '" + resource_item[ "id" ] + "'..." )
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
				print( "Deleting HTTP method '" + http_method + "'..." )
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
		print( "Deleting stage '" + rest_stage[ "stageName" ] + "'..." )
		deletion_futures.append(
			local_tasks.delete_stage(
				credentials,
				api_gateway_id,
				rest_stage[ "stageName" ]
			)
		)
	
	yield deletion_futures
	
	raise gen.Return( api_gateway_id )
	
	
@gen.coroutine
def db_tests():
	test_org_name = "Example Org"
	print( "Creating organization..." )
	new_organization = Organization()
	new_organization.name = test_org_name
	new_organization.max_users = 100
	
	print( "Creating user for organization..." )
	new_user = User()
	new_user.name = "Mark FakeUser"
	new_user.email = "mark@fake.user.example"
	
	new_organization.users.append(
		new_user
	)
	
	print( "Creating another user for organization..." )
	new_user2 = User()
	new_user2.name = "Joe FakeUser"
	new_user2.email = "joe@fake.user.example"
	
	new_organization.users.append(
		new_user2
	)
	
	session.add( new_organization )
	session.commit()
	
	# Retrieve the org and pull out the users
	print( "Pulling the org back..." )
	pulled_org = session.query( Organization ).filter_by(
		name=test_org_name
	).first()
	
	print( "Users from pulled org: " )

	for pulled_user in pulled_org.users:
		print( pulled_user.name + " - " + pulled_user.email )
		
	print( "Pulling a user from the database to get their org..." )
	pulled_user = session.query( User ).filter_by(
		email="mark@fake.user.example"
	).first()
	
	print( "Pulled user: " + pulled_user.name + " - " + pulled_user.email )
	
	print( "Adding email auth token to user..." )
	email_auth_token = EmailAuthToken()
	pulled_user.email_auth_tokens.append(
		email_auth_token
	)
	email_auth_token2 = EmailAuthToken()
	pulled_user.email_auth_tokens.append(
		email_auth_token2
	)
	session.commit()
	
	pulled_user2 = session.query( User ).filter_by(
		email="mark@fake.user.example"
	).first()
	
	print( "Pulled user: " + pulled_user2.name )
	
	for email_token in pulled_user2.email_auth_tokens:
		print( "Email token: " + email_token.token )
		
	print( "Now creating a new project with two deployments." )
	
	project_name = "Example Project"
	
	new_project = Project()
	new_project.name = project_name
	session.add( new_project )
	session.commit()
	
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
		
		self.logit(
			"Processing user registration..."
		)
		
		# Before we continue, check if the email is valid
		try:
			email_validator = validate_email(
				self.json[ "email" ]
			)
			email = email_validator[ "email" ] # replace with normalized form
		except EmailNotValidError as e:
			self.logit( "Invalid email provided during signup!" )
			self.write({
				"success": False,
				"code": "INVALID_EMAIL",
				"msg": str( e ) # The exception string is user-friendly by design.
			})
			raise gen.Return()
			
		# Create new organization for user
		new_organization = Organization()
		new_organization.name = self.json[ "organization_name" ]
		
		# TODO(mandatory): Integration billing before registration
		# is allowed. Also allow for bypass via special registration
		# codes.
		
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
		
		# Check if there are reserved AWS accounts available
		aws_reserved_account = session.query( AWSAccount ).filter_by(
			is_reserved_account=True
		).first()
		
		# If one exists, add it to the account
		if aws_reserved_account != None:
			self.logit( "Adding a reserved AWS account to the newly registered Refinery account..." )
			aws_reserved_account.is_reserved_account = False
			aws_reserved_account.organization_id = new_organization.id
		
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
		
		session.add( new_organization )
		session.commit()
		
		# Send registration confirmation link to user's email address
		# The first time they authenticate via this link it will both confirm
		# their email address and authenticate them.
		self.logit( "Sending user their registration confirmation email..." )
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
		self.logit( "User is authenticating via email link" )
		
		# Query for the provided authentication token
		email_authentication_token = session.query( EmailAuthToken ).filter_by(
			token=str( email_authentication_token )
		).first()
		
		if email_authentication_token == None:
			self.logit( "User's token was not found in the database" )
			self.write( "Invalid authentication token, did you copy the link correctly?" )
			raise gen.Return()
			
		# Calculate token age
		token_age = ( int( time.time() ) - email_authentication_token.timestamp )
		
		# Check if the token is expired
		if email_authentication_token.is_expired == True:
			self.logit( "The user's email token was already marked as expired." )
			self.write( "That email token has expired, please try authenticating again to request a new one." )
			raise gen.Return()
		
		# Check if the token is older than the allowed lifetime
		# If it is then mark it expired and return an error
		if token_age >= int( os.environ.get( "email_token_lifetime" ) ):
			self.logit( "The user's email token was too old and was marked as expired." )
			
			# Mark the token as expired in the database
			email_authentication_token.is_expired = True
			session.commit()
			
			self.write( "That email token has expired, please try authenticating again to request a new one." )
			raise gen.Return()
		
		# Since the user has now authenticated
		# Mark the token as expired in the database
		email_authentication_token.is_expired = True
		
		# Check if the user has previously authenticated via
		# their email address. If not we'll mark their email
		# as validated as well.
		if email_authentication_token.user.email_verified == False:
			email_authentication_token.user.email_verified = True
		
		session.commit()
		
		self.logit( "User authenticated successfully" )
		
		# Authenticate the user via secure cookie
		self.authenticate_user_id(
			email_authentication_token.user.id
		)
		
		self.redirect(
			"/"
		)
	
class GetAuthenticationStatus( BaseHandler ):
	@authenticated
	def get( self ):
		current_user = self.get_authenticated_user()
		
		if current_user:
			self.write({
				"authenticated": True,
				"name": current_user.name,
				"email": current_user.email,
				"permission_level": current_user.permission_level,
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
		
@gen.coroutine
def add_reserved_aws_accounts():
	# Just for testing, this adds AWS accounts to the reserved pool
	# if it is currently empty.
	reserved_aws_accounts_count = session.query( AWSAccount ).filter_by(
		is_reserved_account=True
	).count()
	
	# How many accounts to add
	juice_amount = 100
	
	if reserved_aws_accounts_count == 0:
		print( "No AWS account in reserves, adding " + str( juice_amount ) + " to the pool..." )
		for i in range( 0, 100 ):
			new_aws_account = AWSAccount()
			new_aws_account.account_label = "RefineryLabs Customer Account"
			new_aws_account.is_reserved_account = True
			new_aws_account.account_id = int( os.environ.get( "aws_account_id" ) )
			new_aws_account.access_key = os.environ.get( "aws_access_key" )
			new_aws_account.secret_key = os.environ.get( "aws_secret_key" )
			new_aws_account.region = os.environ.get( "region_name" )
			new_aws_account.lambda_packages_bucket = os.environ.get( "tmp_lambda_packages_bucket" )
			new_aws_account.logs_bucket = os.environ.get( "pipeline_logs_bucket" )
			new_aws_account.iam_admin_username = "DUMMY_VALUE"
			new_aws_account.iam_admin_password = "DUMMY_VALUE"
			session.add( new_aws_account )
			
		session.commit()
		print( "Added new AWS accounts to the pool!" )
		
def make_app( is_debug ):
	tornado_app_settings = {
		"debug": is_debug,
		"cookie_secret": os.environ.get( "cookie_secret_value" )
	}
	
	return tornado.web.Application([
		( r"/authentication/email/([a-z0-9]+)", EmailLinkAuthentication ), # Auth reviewed
		( r"/api/v1/auth/me", GetAuthenticationStatus ), # Auth reviewed
		( r"/api/v1/auth/register", NewRegistration ), # Auth reviewed
		( r"/api/v1/auth/login", Authenticate ), # Auth reviewed
		( r"/api/v1/auth/logout", Logout ), # Auth reviewed
		( r"/api/v1/logs/executions/get", GetProjectExecutionLogs ),
		( r"/api/v1/logs/executions", GetProjectExecutions ), # Auth reviewed *
		( r"/api/v1/aws/deploy_diagram", DeployDiagram ), # Auth reviewed
		( r"/api/v1/functions/delete", SavedFunctionDelete ), # Auth reviewed
		( r"/api/v1/functions/update", SavedFunctionUpdate ), # Auth reviewed
		( r"/api/v1/functions/create", SavedFunctionCreate ), # Auth reviewed
		( r"/api/v1/functions/search", SavedFunctionSearch ), # Auth reviewed
		( r"/api/v1/lambdas/create", SavedLambdaCreate ), # Auth reviewed
		( r"/api/v1/lambdas/search", SavedLambdaSearch ), # Auth reviewed
		( r"/api/v1/lambdas/delete", SavedLambdaDelete ), # Auth reviewed
		( r"/api/v1/lambdas/run", RunLambda ),
		( r"/api/v1/lambdas/logs", GetCloudWatchLogsForLambda ),
		( r"/api/v1/lambdas/env_vars/update", UpdateEnvironmentVariables ),
		( r"/api/v1/aws/run_tmp_lambda", RunTmpLambda ),
		( r"/api/v1/aws/infra_tear_down", InfraTearDown ),
		( r"/api/v1/aws/infra_collision_check", InfraCollisionCheck ),
		( r"/api/v1/projects/save", SaveProject ), # Auth reviewed
		( r"/api/v1/projects/search", SearchSavedProjects ), # Auth reviewed
		( r"/api/v1/projects/get", GetSavedProject ), # Auth reviewed
		( r"/api/v1/projects/delete", DeleteSavedProject ), # Auth reviewed
		( r"/api/v1/projects/config/get", GetProjectConfig ), # Auth reviewed
		( r"/api/v1/deployments/get_latest", GetLatestProjectDeployment ), # Auth reviewed
		( r"/api/v1/deployments/delete_all_in_project", DeleteDeploymentsInProject ) # Auth reviewed
	], **tornado_app_settings)
			
if __name__ == "__main__":
	print( "Starting server..." )
	# Re-initiate things
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
	
	tornado.ioloop.IOLoop.current().run_sync( add_reserved_aws_accounts )
	
	#tornado.ioloop.IOLoop.current().run_sync( delete_logs )
	#tornado.ioloop.IOLoop.current().run_sync( warm_lambda_base_caches )
	
	if os.environ.get( "cf_enabled" ).lower() == "true":
		tornado.ioloop.IOLoop.current().run_sync( get_cloudflare_keys )
		
	server.start()
	tornado.ioloop.IOLoop.current().start()
