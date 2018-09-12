#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
import tornado.escape
import tornado.ioloop
import tornado.web
import subprocess
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

def pprint( input_dict ):
	try:
		print( json.dumps( input_dict, sort_keys=True, indent=4, separators=( ",", ": " ) ) )
	except:
		print( input_dict )
	
class BaseHandler( tornado.web.RequestHandler ):
	def __init__( self, *args, **kwargs ):
		super( BaseHandler, self ).__init__( *args, **kwargs )
		self.set_header( "Access-Control-Allow-Origin", os.environ.get( "access_control_allow_origin" ), )
		self.set_header( "Access-Control-Allow-Headers", "Content-Type, X-CSRF-Validation-Header" )
		self.set_header( "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, HEAD" )
		self.set_header( "Access-Control-Allow-Credentials", "true" )
		self.set_header( "X-Frame-Options", "deny" )
		self.set_header( "Content-Security-Policy", "default-src 'self'" )
		self.set_header( "X-XSS-Protection", "1; mode=block" )
		self.set_header( "X-Content-Type-Options", "nosniff" )
		self.set_header( "Cache-Control", "no-cache, no-store, must-revalidate" )
		self.set_header( "Pragma", "no-cache" )
		self.set_header( "Expires", "0" )

	def logit( self, message, message_type="info" ):
		message = "[" + self.request.remote_ip + "] " + message

		if message_type == "info":
			logging.info( message )
		elif message_type == "warn":
			logging.warn( message )
		elif message_type == "debug":
			logging.debug( message )
		else:
			logging.info( message )
		
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
		def deploy_aws_lambda( self, func_name, description, role_name, zip_data, timeout, memory, vpc_config, env_dict, tags_dict ):
			return TaskSpawner._deploy_aws_lambda( func_name, description, role_name, zip_data, timeout, memory, vpc_config, env_dict, tags_dict )

		@staticmethod
		def _deploy_aws_lambda( func_name, description, role_name, zip_data, timeout, memory, vpc_config, env_dict, tags_dict ):
			"""
			Deploy an AWS Lambda and get it's reference ARN for use
			in later creating an AWS Step Function (SFN)
			"""
			try:
				# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.create_function
				response = LAMBDA_CLIENT.create_function(
					FunctionName=func_name,
					Runtime="python2.7",
					Role=role_name,
					Handler="lambda.main",
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
		def get_lambda_base_zip( libraries ):
			# Check if we have a cache .zip ready to go
			libraries.sort()
			hash_key = hashlib.sha256(
				json.dumps(
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

		@run_on_executor
		def build_lambda( self, code, libraries ):
			return TaskSpawner._build_lambda( code, libraries )
		
		@staticmethod
		def _build_lambda( code, libraries ):
			"""
			Build Lambda package zip and return zip data
			"""
			base_zip_data = TaskSpawner.get_lambda_base_zip(
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
		def create_cloudwatch_rule( self, name, schedule_expression, description ):
			response = EVENTS_CLIENT.put_rule(
				Name=name,
				ScheduleExpression=schedule_expression, # cron(0 20 * * ? *) or rate(5 minutes)
				State="ENABLED",
				Description=description,
				RoleArn=os.environ.get( "events_role" )
			)
			
			return response
			
		@run_on_executor
		def add_rule_target( self, rule_name, target_type, target_id, target_arn, input_dict ):
			targets_data = 	{
				"Id": target_id,
				"Arn": target_arn,
				"Input": json.dumps(
					input_dict
				)
			}
			
			# Supports only lambda and SFNs
			if target_type == "sfn":
				targets_data[ "RoleArn" ] = os.environ.get( "sfn_cloudwatch_role" )
				
			rule_creation_response = EVENTS_CLIENT.put_targets(
				Rule=rule_name,
				Targets=[
					targets_data
				]
			)
			
			if target_type == "lambda":
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
		def create_sqs_queue( self, queue_name, content_based_deduplication ):
			sqs_queue_name = get_lambda_safe_name( queue_name )
			sqs_response = SQS_CLIENT.create_queue(
				QueueName=sqs_queue_name,
				Attributes={
					"DelaySeconds": str( 0 ),
					"MaximumMessageSize": "262144",
					"VisibilityTimeout": str( 300 + 10 ), # Lambda max time plus ten seconds
				}
			)
			
			return "https://console.aws.amazon.com/sqs/home?region=" + os.environ.get( "region_name" ) + "#queue-browser:selected=https://sqs." + os.environ.get( "region_name" ) + ".amazonaws.com/" + os.environ.get( "aws_account_id" ) + "/" + sqs_queue_name + ";noRefresh=true;prefix="
			
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
				"execution_time": {
					"type": "integer",
				},
			},
			"required": [
				"name",
				"language",
				"code",
				"libraries",
				"memory",
				"execution_time",
			]
		}
		
		validate_schema( self.json, schema )
		
		self.logit(
			"Running AWS Lambda..."
		)
		
		lambda_zip_package_data = yield local_tasks.build_lambda(
			self.json[ "code" ],
			self.json[ "libraries" ]
		)
		
		deployed_lambda_data = yield local_tasks.deploy_aws_lambda(
			get_lambda_safe_name(
				self.json[ "name" ]
			),
			"AWS Lambda deployed via refinery",
			os.environ.get( "lambda_role" ),
			lambda_zip_package_data,
			self.json[ "execution_time" ], # Max AWS execution time
			self.json[ "memory" ], # MB of execution memory
			json.loads( os.environ.get( "vpc_data" ) ), # VPC data
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
				"execution_time": {
					"type": "integer",
				},
			},
			"required": [
				"language",
				"code",
				"libraries",
				"memory",
				"execution_time",
			]
		}
		
		validate_schema( self.json, schema )
		
		self.logit(
			"Running AWS Lambda..."
		)
		
		lambda_zip_package_data = yield local_tasks.build_lambda(
			self.json[ "code" ],
			self.json[ "libraries" ]
		)
		
		random_node_id = get_random_node_id()
		
		deployed_lambda_data = yield local_tasks.deploy_aws_lambda(
			random_node_id,
			"AWS Lambda being inline tested.",
			os.environ.get( "lambda_role" ),
			lambda_zip_package_data,
			self.json[ "execution_time" ], # Max AWS execution time
			self.json[ "memory" ], # MB of execution memory
			json.loads( os.environ.get( "vpc_data" ) ), # VPC data
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
		
		cloudwatch_rule_name = get_lambda_safe_name( self.json[ "name" ] )

		print( "Creating new scheduler rule..." )
		rule_data = yield local_tasks.create_cloudwatch_rule(
			cloudwatch_rule_name,
			self.json[ "schedule_expression" ],
			self.json[ "description" ]
		)
		print( "Rule created!" )
		
		print( "Rule data: " )
		print( rule_data )
		
		rule_arn = rule_data[ "RuleArn" ]
		
		print( "Adding target to rule..." )
		
		target_add_data = yield local_tasks.add_rule_target(
			cloudwatch_rule_name,
			self.json[ "target_type" ],
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
			
class DeployStepFunction( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Deploys a Step Function to AWS and executes it.
		
		Returns a link to the AWS SFN execution.
		"""
		self.logit(
			"Deplying step function to AWS..."
		)

		self.logit(
			"Building lambda package..."
		)
		
		lambda_build_futures = []
		lambda_config_datas = []
		
		special_nodes = [
			"start_node",
			"end_node"
		]
		
		sfn_name = get_lambda_safe_name( self.json[ "sfn_name" ] ) + "_" + str( int(time.time()) )
		
		for workflow_state in self.json[ "workflow_states" ]:
			if not workflow_state[ "id" ] in special_nodes:
				lambda_zip_package_data = local_tasks.build_lambda(
					workflow_state[ "code" ],
					workflow_state[ "libraries" ],
				)
				
				lambda_build_futures.append(
					lambda_zip_package_data
				)
				
				lambda_config_datas.append(
					workflow_state
				)
			
		print( "Waiting for all packages to be built..." )
		builds_zip_data_list = yield lambda_build_futures
		print( "Builds complete!" )
		
		# Combine
		lambda_packages = []
		for i in range( 0, len( lambda_config_datas ) ):
			lambda_packages.append({
				"zip": builds_zip_data_list.pop(),
				"config": lambda_config_datas.pop()
			})
		
		print( "Deploying all lambdas..." )
		
		deployed_lambda_futures = []
		lambda_config_datas = []
		
		for lambda_package_data in lambda_packages:
			print( "Lambda data: " )
			pprint(
				lambda_package_data[ "config" ]
			)
			
			deployed_lambda_data = local_tasks.deploy_aws_lambda(
				get_lambda_safe_name( lambda_package_data[ "config" ][ "name" ] ),
				"Example of API deployment of a Lambda function.",
				os.environ.get( "lambda_role" ),
				lambda_package_data[ "zip" ],
				300, # Max AWS execution time
				lambda_package_data[ "config" ][ "memory" ], # MB of execution memory
				json.loads( os.environ.get( "vpc_data" ) ), # VPC data
				{},
				{
					"project": sfn_name
				}
			)
			
			deployed_lambda_futures.append(
				deployed_lambda_data
			)
			
			lambda_config_datas.append(
				lambda_package_data[ "config" ]
			)
			
		print( "Waiting for deployments to finish..." )
		deployed_lambda_results = yield deployed_lambda_futures
		print( "Deployments complete!" )
		
		deployed_arns_list = []
		
		# Combined
		for i in range( 0, len( lambda_config_datas ) ):
			deployed_arns_list.append({
				"config": lambda_config_datas.pop(),
				"deploy_result": deployed_lambda_results.pop()
			})
		
		print( "Deployed ARNs: " )
		pprint(
			deployed_arns_list
		)
		
		name_to_arn_map = {}
		for deployed_arn_data in deployed_arns_list:
			name_to_arn_map[ get_lambda_safe_name( deployed_arn_data[ "config" ][ "name" ] ) ] = deployed_arn_data[ "deploy_result" ][ "FunctionArn" ]
			
		print( "Name to ARN map: " )
		pprint( name_to_arn_map )
		
		aws_step_function_data = refinery_to_aws_step_function(
			self.json,
			name_to_arn_map,
		)
		
		print( "Step function data: " )
		pprint(
			aws_step_function_data
		)
		
		print( "Deploying Step Function..." )
		deployed_step_function_data = yield local_tasks.deploy_aws_step_function(
			sfn_name,
			aws_step_function_data,
			os.environ.get( "sfn_role" ),
		)
		print( "Step function deployed!" )
		
		step_function_arn = deployed_step_function_data[ "stateMachineArn" ]
		
		print( "Executing Step Function..." )
		executed_step_function_data = yield local_tasks.execute_aws_step_function(
			"autoexecutionexample",
			step_function_arn,
			{}
		)
		print( "Step function executed!" )
		print(
			executed_step_function_data
		)
		
		exection_arn = executed_step_function_data[ "executionArn" ]
		
		execution_status_url = "https://us-west-2.console.aws.amazon.com/states/home?region=" + os.environ.get( "region_name" ) + "#/executions/details/" + exection_arn
		
		print( "Execution status URL: " )
		print(
			execution_status_url
		)
		
		self.write({
			"success": True,
			"result": {
				"url": execution_status_url,
				"sfn_arn": step_function_arn,
				"sfn_name": sfn_name,
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
				}
			},
			"required": [
				"name",
				"description",
				"code",
				"language"
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
		
		session.add( new_function )
		session.commit()
		
		self.write({
			"success": True,
			"id": new_function.id
		})
		
def make_app( is_debug ):
	# Convert to bool
	is_debug = ( is_debug.lower() == "true" )
	
	tornado_app_settings = {
		"debug": is_debug,
	}
	
	return tornado.web.Application([
		( r"/api/v1/functions/create", SavedFunctionCreate ),
		( r"/api/v1/functions/search", SavedFunctionSearch ),
		( r"/api/v1/aws/create_schedule_trigger", CreateScheduleTrigger ),
		( r"/api/v1/aws/deploy_step_function", DeployStepFunction ),
		( r"/api/v1/aws/deploy_lambda", DeployLambda ),
		( r"/api/v1/aws/run_tmp_lambda", RunTmpLambda ),
		( r"/api/v1/aws/create_sqs_trigger", CreateSQSQueueTrigger )
	], **tornado_app_settings)
			
if __name__ == "__main__":
	print( "Starting server..." )
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