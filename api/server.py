#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
import tornado.escape
import tornado.ioloop
import tornado.web
import subprocess
import autopep8
import logging
import hashlib
import shutil
import base64
import boto3
import uuid
import json
import yaml
import copy
import time
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
from models.initiate_database import *
from models.saved_function import SavedFunction

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

# Debugging shunt for setting environment variables from yaml
with open( "config.yaml", "r" ) as file_handler:
    settings = yaml.safe_load(
        file_handler.read()
    )
    for key, value in settings.iteritems():
        os.environ[ key ] = str( value )

def on_start():
	global LAMDBA_BASE_CODES, LAMBDA_BASE_LIBRARIES, LAMBDA_SUPPORTED_LANGUAGES
	LAMDBA_BASE_CODES = {}
	LAMBDA_BASE_LIBRARIES = {
		"python2.7": [
			"redis",
			"boto3"
		],
		"nodejs8.10": [
			"redis",
		]
	}
	
	LAMBDA_SUPPORTED_LANGUAGES = [
		"python2.7",
		"nodejs8.10",
	]
	
	for language_name, libraries in LAMBDA_BASE_LIBRARIES.iteritems():
		# Load Lambda base templates
		with open( "./lambda_bases/" + language_name, "r" ) as file_handler:
			LAMDBA_BASE_CODES[ language_name ] = file_handler.read().replace(
				"{{REDIS_PASSWORD_REPLACE_ME}}",
				os.environ.get( "lambda_redis_password" )
			)
        
S3_CLIENT = boto3.client(
    "s3",
    aws_access_key_id=os.environ.get( "aws_access_key" ),
    aws_secret_access_key=os.environ.get( "aws_secret_key" ),
)

LAMBDA_CLIENT = boto3.client(
    "lambda",
    aws_access_key_id=os.environ.get( "aws_access_key" ),
    aws_secret_access_key=os.environ.get( "aws_secret_key" ),
    region_name=os.environ.get( "region_name" )
)

SFN_CLIENT = boto3.client(
    "stepfunctions",
    aws_access_key_id=os.environ.get( "aws_access_key" ),
    aws_secret_access_key=os.environ.get( "aws_secret_key" ),
    region_name=os.environ.get( "region_name" )
)

EVENTS_CLIENT = boto3.client(
	"events",
    aws_access_key_id=os.environ.get( "aws_access_key" ),
    aws_secret_access_key=os.environ.get( "aws_secret_key" ),
    region_name=os.environ.get( "region_name" )
)

SQS_CLIENT = boto3.client(
	"sqs",
    aws_access_key_id=os.environ.get( "aws_access_key" ),
    aws_secret_access_key=os.environ.get( "aws_secret_key" ),
    region_name=os.environ.get( "region_name" )
)

SNS_CLIENT = boto3.client(
	"sns",
    aws_access_key_id=os.environ.get( "aws_access_key" ),
    aws_secret_access_key=os.environ.get( "aws_secret_key" ),
    region_name=os.environ.get( "region_name" )
)

CLOUDWATCH_LOGS_CLIENT = boto3.client(
	"logs",
    aws_access_key_id=os.environ.get( "aws_access_key" ),
    aws_secret_access_key=os.environ.get( "aws_secret_key" ),
    region_name=os.environ.get( "region_name" )
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

	def logit( self, message, message_type="info" ):
		message = "[" + self.request.remote_ip + "] " + message
		
		logit( message )
		
	def prepare( self ):
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
	
class TaskSpawner(object):
		def __init__(self, loop=None):
			self.executor = futures.ThreadPoolExecutor( 60 )
			self.loop = loop or tornado.ioloop.IOLoop.current()
			
		@run_on_executor
		def execute_aws_lambda( self, arn, input_data ):
			return TaskSpawner._execute_aws_lambda( arn, input_data )
		
		@staticmethod
		def _execute_aws_lambda( arn, input_data ):
			response = LAMBDA_CLIENT.invoke(
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
				log_output = "\n".join( log_lines[ 1:-3 ] )
				
			return {
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
		def execute_aws_step_function( self, exec_name, sfn_arn, input_data ):
			return TaskSpawner._execute_aws_step_function( exec_name, sfn_arn, input_data )
		
		@staticmethod
		def _execute_aws_step_function( exec_name, sfn_arn, input_data ):
			response = SFN_CLIENT.start_execution(
				stateMachineArn=sfn_arn,
				name=exec_name,
				input=json.dumps(
					input_data
				)
			)
			
			return response
			
		@run_on_executor
		def deploy_aws_step_function( self, sfn_name, sfn_definition, role_name ):
			return TaskSpawner._deploy_aws_step_function( sfn_name, sfn_definition, role_name )

		@staticmethod
		def _deploy_aws_step_function( sfn_name, sfn_definition, role_name ):
			"""
			Deploy an AWS step function
			"""
			response = SFN_CLIENT.create_state_machine(
				name=sfn_name,
				definition=json.dumps(
					sfn_definition
				),
				roleArn=role_name
			)
			return response
			
		@run_on_executor
		def delete_aws_lambda( self, arn_or_name ):
			return TaskSpawner._delete_aws_lambda( arn_or_name )
		
		@staticmethod
		def _delete_aws_lambda( arn_or_name ):
			response = LAMBDA_CLIENT.delete_function(
				FunctionName=arn_or_name
			)
			
			return response
			
		@run_on_executor
		def deploy_aws_lambda( self, func_name, language, description, role_name, zip_data, timeout, memory, vpc_config, env_dict, tags_dict ):
			return TaskSpawner._deploy_aws_lambda( func_name, language, description, role_name, zip_data, timeout, memory, vpc_config, env_dict, tags_dict )

		@staticmethod
		def _deploy_aws_lambda( func_name, language, description, role_name, zip_data, timeout, memory, vpc_config, env_dict, tags_dict ):
			"""
			Deploy an AWS Lambda and get it's reference ARN for use
			in later creating an AWS Step Function (SFN)
			"""
			try:
				# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.create_function
				response = LAMBDA_CLIENT.create_function(
					FunctionName=func_name,
					Runtime=language,
					Role=role_name,
					Handler="lambda._init",
					Code={
						"ZipFile": zip_data,
					},
					Description=description,
					Timeout=timeout,
					MemorySize=memory,
					Publish=True,
					VpcConfig=vpc_config,
					Environment={
						"Variables": env_dict
					},
					Tags=tags_dict
				)
			except ClientError as e:
				if e.response[ "Error" ][ "Code" ] == "ResourceConflictException":
					print( "Duplicate! Deleting previous to replace it..." )
					
					# Delete the existing lambda
					delete_response = TaskSpawner._delete_aws_lambda(
						func_name
					)
					
					# Now create it since we're clear
					return TaskSpawner._deploy_aws_lambda(
						func_name,
						language,
						description,
						role_name,
						zip_data,
						timeout,
						memory,
						vpc_config,
						env_dict,
						tags_dict
					)
				else:
					return False
			
			# response[ "MasterArn" ]
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
			
			# Use npm to create node_modules from package.json
			npm_process = subprocess.Popen(
				"/usr/bin/npm install package.json",
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				cwd=build_directory
			)
			stdout, stderr = npm_process.communicate()
			
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
		def _build_nodejs_810_lambda( code, libraries, transitions ):
			"""
			Build Lambda package zip and return zip data
			"""
			
			"""
			Inject base libraries (e.g. redis) into lambda
			and the init code.
			"""
			
			print( "Building node 8.10 lambda..." )
			
			code = LAMDBA_BASE_CODES[ "nodejs8.10" ] + "\n\n" + code
			
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
				
			with zipfile.ZipFile( tmp_zip_file, "a" ) as zip_file_handler:
				info = zipfile.ZipInfo(
					"lambda.js"
				)
				info.external_attr = 0777 << 16L
				
				# Write lambda.py into new .zip
				zip_file_handler.writestr(
					info,
					code
				)
				
			with open( tmp_zip_file, "rb" ) as file_handler:
				zip_data = file_handler.read()
			
			# Delete zip file now that we've read it
			os.remove( tmp_zip_file )
			
			return zip_data

		@run_on_executor
		def build_lambda( self, language, code, libraries, transitions ):
			if not ( language in LAMBDA_SUPPORTED_LANGUAGES ):
				raise "Error, this language is not yet supported by refinery!"
			
			if language == "python2.7":
				return TaskSpawner._build_python_lambda( code, libraries, transitions )
			elif language == "nodejs8.10":
				return TaskSpawner._build_nodejs_810_lambda( code, libraries, transitions )
		
		@staticmethod
		def _build_python_lambda( code, libraries, transitions ):
			"""
			Build Lambda package zip and return zip data
			"""
			
			"""
			Inject base libraries (e.g. redis) into lambda
			and the init code.
			"""
			
			code = LAMDBA_BASE_CODES[ "python2.7" ] + "\n\n" + code
			code = autopep8.fix_code(
				code,
				options={
					"select": [
						"E101",
					]
				}
			)
			
			code = code.replace( "\"{{TRANSITION_DATA_REPLACE_ME}}\"", json.dumps( json.dumps( transitions ) ) )
			code = code.replace( "{{AWS_REGION_REPLACE_ME}}", os.environ.get( "region_name" ) )
			
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
				
			with zipfile.ZipFile( tmp_zip_file, "a" ) as zip_file_handler:
				info = zipfile.ZipInfo(
					"lambda.py"
				)
				info.external_attr = 0777 << 16L
				
				# Write lambda.py into new .zip
				zip_file_handler.writestr(
					info,
					code
				)
				
			with open( tmp_zip_file, "rb" ) as file_handler:
				zip_data = file_handler.read()
			
			# Delete zip file now that we've read it
			os.remove( tmp_zip_file )
			
			return zip_data
			
		@run_on_executor
		def create_cloudwatch_rule( self, id, name, schedule_expression, description, input_dict ):
			response = EVENTS_CLIENT.put_rule(
				Name=name,
				ScheduleExpression=schedule_expression, # cron(0 20 * * ? *) or rate(5 minutes)
				State="ENABLED",
				Description=description,
				RoleArn=os.environ.get( "events_role" )
			)
			
			return {
				"id": id,
				"name": name,
				"arn": response[ "RuleArn" ],
				"input_dict": input_dict,
			}
			
		@run_on_executor
		def add_rule_target( self, rule_name, target_id, target_arn, input_dict ):
			targets_data = 	{
				"Id": target_id,
				"Arn": target_arn,
				"Input": json.dumps(
					input_dict
				)
			}
			
			rule_creation_response = EVENTS_CLIENT.put_targets(
				Rule=rule_name,
				Targets=[
					targets_data
				]
			)
			
			"""
			For AWS Lambda you need to add a permission to the Lambda function itself
			via the add_permission API call to allow invocation via the CloudWatch event.
			"""
			lambda_permission_add_response = LAMBDA_CLIENT.add_permission(
				FunctionName=target_arn,
				StatementId=rule_name + "_statement",
				Action="lambda:*",
				Principal="events.amazonaws.com",
				SourceArn="arn:aws:events:" + os.environ.get( "region_name" ) + ":" + os.environ.get( "aws_account_id" ) + ":rule/" + rule_name,
				#SourceAccount=os.environ.get( "aws_account_id" ) # THIS IS A BUG IN AWS NEVER PASS THIS
			)
			
			print( "Lambda add permission: " )
			pprint( lambda_permission_add_response )
			
			return rule_creation_response
		
		@run_on_executor
		def create_sns_topic( self, id, topic_name ):
			topic_name = get_lambda_safe_name( topic_name )
			response = SNS_CLIENT.create_topic(
				Name=topic_name
			)
			
			return {
				"id": id,
				"name": topic_name,
				"arn": response[ "TopicArn" ],
				"topic_name": topic_name
			}
			
		@run_on_executor
		def subscribe_lambda_to_sns_topic( self, topic_name, topic_arn, lambda_arn ):
			"""
			For AWS Lambda you need to add a permission to the Lambda function itself
			via the add_permission API call to allow invocation via the SNS event.
			"""
			lambda_permission_add_response = LAMBDA_CLIENT.add_permission(
				FunctionName=lambda_arn,
				StatementId=str( uuid.uuid4() ),
				Action="lambda:*",
				Principal="sns.amazonaws.com",
				SourceArn=topic_arn,
				#SourceAccount=os.environ.get( "aws_account_id" ) # THIS IS A BUG IN AWS NEVER PASS THIS
			)
			
			sns_topic_response = SNS_CLIENT.subscribe(
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
		def create_sqs_queue( self, id, queue_name, content_based_deduplication, batch_size ):
			sqs_queue_name = get_lambda_safe_name( queue_name )
			sqs_response = SQS_CLIENT.create_queue(
				QueueName=sqs_queue_name,
				Attributes={
					"DelaySeconds": str( 0 ),
					"MaximumMessageSize": "262144",
					"VisibilityTimeout": str( 300 + 10 ), # Lambda max time plus ten seconds
				}
			)
			
			sqs_arn = "arn:aws:sqs:" + os.environ.get( "region_name" ) + ":" + os.environ.get( "aws_account_id" ) + ":" + queue_name
			
			return {
				"id": id,
				"queue_name": queue_name,
				"arn": sqs_arn,
				"batch_size": batch_size
			}
			
		@run_on_executor
		def map_sqs_to_lambda( self, sqs_arn, lambda_arn, batch_size ):
			response = LAMBDA_CLIENT.create_event_source_mapping(
				EventSourceArn=sqs_arn,
				FunctionName=lambda_arn,
				Enabled=True,
				BatchSize=batch_size,
			)
			
			print( "Mapping SQS to lambda: " )
			pprint(
				response
			)
			
			return response
			
		@run_on_executor
		def get_cloudwatch_logs( self, log_group_name, log_stream_name ):
			response = CLOUDWATCH_LOGS_CLIENT.get_log_events(
				logGroupName=log_group_name,
				logStreamName=log_stream_name,
				#nextToken='string',
				#limit=123,
				startFromHead=True
			)
			
			print( "Get Cloudwatch Logs: " )
			pprint( response )
			
			return response
			
		@run_on_executor
		def write_to_s3( self, s3_bucket, path, object_data ):
			# Remove leading / because they are almost always not intended
			if path.startswith( "/" ):
				path = path[1:]
				
			response = S3_CLIENT.put_object(
				Key=path,
				Bucket=s3_bucket,
				Body=object_data,
			)
			
			return response
			
		@run_on_executor
		def read_from_s3( self, s3_bucket, path ):
			# Remove leading / because they are almost always not intended
			if path.startswith( "/" ):
				path = path[1:]
				
			try:
				s3_object = S3_CLIENT.get_object(
					Bucket=s3_bucket,
					Key=path
				)
			except:
				return "{}"
				
			return s3_object[ "Body" ].read()
			
local_tasks = TaskSpawner()
			
def get_random_node_id():
	return "n" + str( uuid.uuid4() ).replace( "-", "" )
	
class DeployLambda( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Deploy a given Lambda standalone
		"""
		schema = {
			"type": "object",
			"properties": {
				"name": {
					"type": "string",
				},
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
			},
			"required": [
				"name",
				"language",
				"code",
				"libraries",
				"memory",
				"max_execution_time",
			]
		}
		
		validate_schema( self.json, schema )
		
		self.logit(
			"Running AWS Lambda..."
		)
		
		lambda_zip_package_data = yield local_tasks.build_lambda(
			self.json[ "language" ],
			self.json[ "code" ],
			self.json[ "libraries" ],
			[]
		)
		
		deployed_lambda_data = yield local_tasks.deploy_aws_lambda(
			get_lambda_safe_name(
				self.json[ "name" ]
			),
			self.json[ "language" ],
			"AWS Lambda deployed via refinery",
			os.environ.get( "lambda_role" ),
			lambda_zip_package_data,
			self.json[ "max_execution_time" ], # Max AWS execution time
			self.json[ "memory" ], # MB of execution memory
			{}, # VPC data
			{},
			{
				"project": "None"
			}
		)
		
		self.write({
			"success": True,
			"arn": deployed_lambda_data[ "FunctionArn" ],
			"url": "https://console.aws.amazon.com/lambda/home?region=" + os.environ.get( "region_name" ) + "#/functions/" + deployed_lambda_data[ "FunctionArn" ] + "?tab=graph",
			"name": get_lambda_safe_name(
				self.json[ "name" ]
			),
		})

class RunTmpLambda( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Build, deploy, and run an AWS lambda function.
		
		Always upon completion the Lambda should be deleted!
		"""
		schema = {
			"type": "object",
			"properties": {
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
			},
			"required": [
				"language",
				"code",
				"libraries",
				"memory",
				"max_execution_time",
			]
		}
		
		validate_schema( self.json, schema )
		
		self.logit(
			"Running AWS Lambda..."
		)
		
		lambda_zip_package_data = yield local_tasks.build_lambda(
			self.json[ "language" ],
			self.json[ "code" ],
			self.json[ "libraries" ],
			{
				"then": False,
				"else": False,
				"exception": False,
				"if": []
			}
		)
		
		random_node_id = get_random_node_id()
		
		deployed_lambda_data = yield local_tasks.deploy_aws_lambda(
			random_node_id,
			self.json[ "language" ],
			"AWS Lambda being inline tested.",
			os.environ.get( "lambda_role" ),
			lambda_zip_package_data,
			self.json[ "max_execution_time" ], # Max AWS execution time
			self.json[ "memory" ], # MB of execution memory
			{}, # VPC data
			{},
			{
				"project": "None"
			}
		)
		
		lambda_result = yield local_tasks.execute_aws_lambda(
			deployed_lambda_data[ "FunctionArn" ],
			{}
		)

		# Now we delete the lambda, don't yield because we don't need to wait
		delete_result = local_tasks.delete_aws_lambda(
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
	
class CreateScheduleTrigger( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Creates a scheduled trigger for a given SFN or Lambda.
		"""
		self.logit(
			"Creating scheduled trigger..."
		)
		
		schema = {
			"type": "object",
			"properties": {
				"name": {
					"type": "string",
				},
				"schedule_expression": {
					"type": "string",
				},
				"description": {
					"type": "string",
				},
				"target_arn": {
					"type": "string",
				},
				"target_id": {
					"type": "string",
				},
				"target_type": {
					"type": "string"
				}
			},
			"required": [
				"name",
				"schedule_expression",
				"description",
				"target_arn",
				"input_dict",
				"target_id",
				"target_type"
			]
		}
		
		validate_schema( self.json, schema )

		print( "Creating new scheduler rule..." )
		rule_data = yield local_tasks.create_cloudwatch_rule(
			cloudwatch_rule_name,
			self.json[ "schedule_expression" ],
			self.json[ "description" ],
			{},
		)
		print( "Rule created!" )
		
		print( "Rule data: " )
		print( rule_data )
		
		rule_arn = rule_data[ "RuleArn" ]
		
		print( "Adding target to rule..." )
		
		target_add_data = yield local_tasks.add_rule_target(
			cloudwatch_rule_name,
			self.json[ "target_id" ],
			self.json[ "target_arn" ],
			self.json[ "input_dict" ]
		)
		
		print("Target added!")
		
		print( "Target added data: " )
		pprint( target_add_data )
		
		self.write({
			"success": True,
			"result": {
				"rule_arn": rule_arn,
				"url": "https://console.aws.amazon.com/cloudwatch/home?region=" + os.environ.get( "region_name" ) + "#rules:name=" + cloudwatch_rule_name
			}
		})
		
class CreateSQSQueueTrigger( BaseHandler ):
	@gen.coroutine
	def post( self ):
		self.logit(
			"Deploying SQS Queue..."
		)
		
		schema = {
			"type": "object",
			"properties": {
				"queue_name": {
					"type": "string",
				},
				"lambda_arn": {
					"type": "string",
				},
				"batch_size": {
					"type": "integer"
				},
				"content_based_deduplication": {
					"type": "boolean",
				}
			},
			"required": [
				"queue_name",
				"content_based_deduplication",
				"lambda_arn",
				"batch_size",
			]
		}
		
		validate_schema( self.json, schema )
		
		sqs_queue_name = get_lambda_safe_name(
			self.json[ "queue_name" ]
		)
		
		sqs_queue_url = yield local_tasks.create_sqs_queue(
			sqs_queue_name,
			self.json[ "content_based_deduplication" ]
		)
		
		sqs_arn = "arn:aws:sqs:" + os.environ.get( "region_name" ) + ":" + os.environ.get( "aws_account_id" ) + ":" + sqs_queue_name
		
		sqs_lambda_map_result = yield local_tasks.map_sqs_to_lambda(
			sqs_arn,
			self.json[ "lambda_arn" ],
			self.json[ "batch_size" ]
		)
		
		print( "Map result: " )
		pprint(
			sqs_lambda_map_result
		)
		
		self.write({
			"success": True,
			"queue_url": sqs_queue_url
		})
		
class SavedFunctionSearch( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""

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
		
		if self.json[ "query" ] == "":
			self.write({
				"success": True,
				"results": []
			})
			raise gen.Return()
		
		# First search names
		name_search_results = session.query( SavedFunction ).filter(
			SavedFunction.name.ilike( "%" + self.json[ "query" ] + "%" ) # Probably SQL injection \o/
		).limit(10).all()
		
		# Second search descriptions
		description_search_results = session.query( SavedFunction ).filter(
			SavedFunction.description.ilike( "%" + self.json[ "query" ] + "%" ) # Probably SQL injection \o/
		).limit(10).all()
		
		already_added_ids = []
		results_list = []
		
		"""
		The below ranks saved function "name" matches over description matches.
		"""
		for name_search_result in name_search_results:
			if not name_search_result.id in already_added_ids:
				already_added_ids.append(
					name_search_result.id
				)
				
				results_list.append(
					name_search_result.to_dict()
				)
				
		for description_search_result in description_search_results:
			if not description_search_result.id in already_added_ids:
				already_added_ids.append(
					description_search_result.id
				)
				
				results_list.append(
					description_search_result.to_dict()
				)
		
		self.write({
			"success": True,
			"results": results_list
		})
		
class SavedFunctionCreate( BaseHandler ):
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
		
		session.add( new_function )
		session.commit()
		
		self.write({
			"success": True,
			"id": new_function.id
		})
		
class SavedFunctionUpdate( BaseHandler ):
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
			"Deleting function data..."
		)
		
		session.query( SavedFunction ).filter_by(
			id=self.json[ "id" ]
		).delete()
		
		session.commit()
		
		self.write({
			"success": True
		})
		
class SaveSQSJobTemplate( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Save SQS job template to S3
		"""
		schema = {
			"type": "object",
			"properties": {
				"job_template": {
					"type": "string",
				},
				"queue_name": {
					"type": "string",
				}
			},
			"required": [
				"job_template",
				"queue_name"
			]
		}
		
		validate_schema( self.json, schema )
		
		self.logit(
			"Writing job template..."
		)
		
		yield local_tasks.write_to_s3(
			os.environ.get( "sqs_job_templates_s3_bucket" ),
			self.json[ "queue_name" ],
			self.json[ "job_template" ]
		)
		
		self.write({
			"success": True
		})
		
class GetSQSJobTemplate( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Retrieve an SQS template from S3
		"""
		schema = {
			"type": "object",
			"properties": {
				"queue_name": {
					"type": "string",
				}
			},
			"required": [
				"queue_name"
			]
		}
		
		validate_schema( self.json, schema )
		
		self.logit(
			"Retrieving job template..."
		)
		
		job_template = yield local_tasks.read_from_s3(
			os.environ.get( "sqs_job_templates_s3_bucket" ),
			self.json[ "queue_name" ]
		)
		
		self.write({
			"success": True,
			"job_template": job_template
		})
		
@gen.coroutine
def deploy_lambda( id, name, language, code, libraries, max_execution_time, memory, transitions ):
	logit(
		"Building '" + name + "' Lambda package..."
	)
	
	lambda_zip_package_data = yield local_tasks.build_lambda(
		language,
		code,
		libraries,
		transitions
	)
	
	logit(
		"Deploying '" + name + "' Lambda package to production..."
	)

	deployed_lambda_data = yield local_tasks.deploy_aws_lambda(
		name,
		language,
		"AWS Lambda deployed via refinery",
		os.environ.get( "lambda_role" ),
		lambda_zip_package_data,
		max_execution_time, # Max AWS execution time
		memory, # MB of execution memory
		{}, # VPC data
		{},
		{
			"refinery_id": id,
		}
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
def deploy_diagram( diagram_data ):
	"""
	Deploy the diagram to AWS
	"""
	
	"""
	Process workflow relationships and tag Lambda
	nodes with an array of transitions.
	"""
	# First just set an empty array for each lambda node
	for workflow_state in diagram_data[ "workflow_states" ]:
		if workflow_state[ "type" ] == "lambda":
			# Set up default transitions data
			workflow_state[ "transitions" ] = {}
			workflow_state[ "transitions" ][ "if" ] = []
			workflow_state[ "transitions" ][ "else" ] = False
			workflow_state[ "transitions" ][ "exception" ] = False
			workflow_state[ "transitions" ][ "then" ] = False
		
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
		
		if origin_node_data[ "type" ] == "lambda":
			target_arn = "arn:aws:lambda:" + os.environ.get( "region_name" ) + ":" + os.environ.get( "aws_account_id" ) + ":function:" + get_lambda_safe_name( target_node_data[ "name" ] )
			
			if workflow_relationship[ "type" ] == "then":
				origin_node_data[ "transitions" ][ "then" ] = target_arn
			elif workflow_relationship[ "type" ] == "else":
				origin_node_data[ "transitions" ][ "else" ] = target_arn
			elif workflow_relationship[ "type" ] == "exception":
				origin_node_data[ "transitions" ][ "exception" ] = target_arn
			elif workflow_relationship[ "type" ] == "if":
				origin_node_data[ "transitions" ][ "if" ].append({
					"target_arn": target_arn,
					"type": workflow_relationship[ "type" ],
					"expression": workflow_relationship[ "expression" ]
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
	
	"""
	Deploy all Lambdas to production
	"""
	lambda_node_deploy_futures = []
	
	for lambda_node in lambda_nodes:
		lambda_node_deploy_futures.append(
			deploy_lambda(
				lambda_node[ "id" ],
				get_lambda_safe_name( lambda_node[ "name" ] ),
				lambda_node[ "language" ],
				lambda_node[ "code" ],
				lambda_node[ "libraries" ],
				lambda_node[ "max_execution_time" ],
				lambda_node[ "memory" ],
				lambda_node[ "transitions" ],
			)
		)
		
	"""
	Deploy all time triggers to production
	"""
	schedule_trigger_node_deploy_futures = []
	
	for schedule_trigger_node in schedule_trigger_nodes:
		schedule_trigger_name = get_lambda_safe_name( schedule_trigger_node[ "name" ] )
		logit( "Deploying schedule trigger '" + schedule_trigger_name + "'..." )
		schedule_trigger_node_deploy_futures.append(
			local_tasks.create_cloudwatch_rule(
				schedule_trigger_node[ "id" ],
				schedule_trigger_name,
				schedule_trigger_node[ "schedule_expression" ],
				schedule_trigger_node[ "description" ],
				schedule_trigger_node[ "input_dict" ],
			)
		)
		
	"""
	Deploy all SQS queues to production
	"""
	sqs_queue_nodes_deploy_futures = []
	
	for sqs_queue_node in sqs_queue_nodes:
		sqs_queue_name = get_lambda_safe_name( sqs_queue_node[ "name" ] )
		logit( "Deploying SQS queue '" + sqs_queue_name + "'..." )
		sqs_queue_nodes_deploy_futures.append(
			local_tasks.create_sqs_queue(
				sqs_queue_node[ "id" ],
				sqs_queue_name,
				sqs_queue_node[ "content_based_deduplication" ],
				sqs_queue_node[ "batch_size" ] # Not used, passed along
			)
		)
		
	"""
	Deploy all SNS topics to production
	"""
	sns_topic_nodes_deploy_futures = []
	
	for sns_topic_node in sns_topic_nodes:
		sns_topic_name = get_lambda_safe_name( sns_topic_node[ "name" ] )
		logit( "Deploying SNS topic '" + sns_topic_name + "'..." )
		sns_topic_nodes_deploy_futures.append(
			local_tasks.create_sns_topic(
				sns_topic_node[ "id" ],
				sns_topic_node[ "topic_name" ],
			)
		)
		
	# Wait till everything is deployed
	deployed_lambdas = yield lambda_node_deploy_futures
	deployed_schedule_triggers = yield schedule_trigger_node_deploy_futures
	deployed_sqs_queues = yield sqs_queue_nodes_deploy_futures
	deployed_sns_topics = yield sns_topic_nodes_deploy_futures
	
	"""
	Update all nodes with deployed ARN for easier teardown
	"""
	# Update workflow lambda nodes with arn
	for deployed_lambda in deployed_lambdas:
		for workflow_state in diagram_data[ "workflow_states" ]:
			if workflow_state[ "id" ] == deployed_lambda[ "id" ]:
				workflow_state[ "arn" ] = deployed_lambda[ "arn" ]
				workflow_state[ "name" ] = deployed_lambda[ "name" ]
				
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
	
	raise gen.Return(
		diagram_data
	)
		
class DeployDiagram( BaseHandler ):
	@gen.coroutine
	def post( self ):
		self.logit(
			"Deploying diagram to production..."
		)
		
		diagram_data = json.loads( self.json[ "diagram_data" ] )
		
		results_data = yield deploy_diagram( diagram_data )
		
		self.write({
			"success": True,
			"result": diagram_data
		})
		
def make_app( is_debug ):
	# Convert to bool
	is_debug = ( is_debug.lower() == "true" )
	
	tornado_app_settings = {
		"debug": is_debug,
	}
	
	return tornado.web.Application([
		( r"/api/v1/aws/deploy_diagram", DeployDiagram ),
		( r"/api/v1/sqs/job_template/get", GetSQSJobTemplate ),
		( r"/api/v1/sqs/job_template", SaveSQSJobTemplate ),
		( r"/api/v1/functions/delete", SavedFunctionDelete ),
		( r"/api/v1/functions/update", SavedFunctionUpdate ),
		( r"/api/v1/functions/create", SavedFunctionCreate ),
		( r"/api/v1/functions/search", SavedFunctionSearch ),
		( r"/api/v1/aws/create_schedule_trigger", CreateScheduleTrigger ),
		( r"/api/v1/aws/deploy_lambda", DeployLambda ),
		( r"/api/v1/aws/run_tmp_lambda", RunTmpLambda ),
		( r"/api/v1/aws/create_sqs_trigger", CreateSQSQueueTrigger )
	], **tornado_app_settings)
			
if __name__ == "__main__":
	print( "Starting server..." )
	# Re-initiate things
	on_start()
	app = make_app( "true" )
	server = tornado.httpserver.HTTPServer(
		app
	)
	server.bind(
		7777
	)
	Base.metadata.create_all( engine )
	server.start()
	tornado.ioloop.IOLoop.current().start()