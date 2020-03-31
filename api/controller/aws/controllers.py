import json
import time

import botocore
import pinject
from jsonschema import validate as validate_schema
from tornado import gen

from assistants.deployments.teardown import teardown_infrastructure
from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from controller import BaseHandler
from controller.aws.actions import get_layers_for_lambda, get_environment_variables_for_lambda, deploy_lambda, \
	get_base_lambda_code, get_lambda_safe_name, deploy_diagram
from controller.aws.schemas import *
from controller.decorators import authenticated, disable_on_overdue_payment
from controller.logs.actions import delete_logs
from controller.projects.actions import update_project_config
from data_types.aws_resources.alambda import Lambda
from models import InlineExecutionLambda, Project, Deployment
from pyexceptions.builds import BuildException
from utils.general import get_random_node_id, attempt_json_decode


class RunTmpLambdaDependencies:
	@pinject.copy_args_to_public_fields
	def __init__( self, builder_manager ):
		pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class RunTmpLambda( BaseHandler ):
	dependencies = RunTmpLambdaDependencies
	builder_manager = None

	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		"""
		Build, deploy, and run an AWS lambda function.

		Always upon completion the Lambda should be deleted!
		"""
		validate_schema( self.json, RUN_TMP_LAMBDA_SCHEMA )

		self.logger( "Building Lambda package..." )

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

		# Check if we already have an inline execution Lambda for it.
		cached_inline_execution_lambda = self.dbsession.query( InlineExecutionLambda ).filter_by(
			aws_account_id=credentials[ "id" ],
			unique_hash_key=inline_lambda_hash_key
		).first()

		# We can skip this if we already have a cached execution
		if cached_inline_execution_lambda:
			self.logger( "Inline execution is already cached as a Lambda, doing a hotload..." )

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
					self.task_spawner,
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
				self.logger( "An exception occurred while setting up the Code Block." )
				self.logger( boto_error )

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
			self.app_config,
			self.json[ "language" ],
			self.json[ "code" ]
		)

		if self.json[ "language" ] == "go1.12":
			inline_lambda.code = inline_execution_code

			try:
				binary_s3_path = yield self.builder_manager.get_go112_binary_s3(
					credentials,
					inline_lambda
				)
			except BuildException as build_exception:
				self.write({
					"success": False,
					"msg": "An error occurred while building the Code Block package.",
					"log_output": build_exception.build_output
				})
				raise gen.Return()

			execute_lambda_params[ "_refinery" ][ "inline_code" ] = {
				"s3_path": binary_s3_path,
				"shared_files": self.json[ "shared_files" ]
			}
		else:
			# Generate Lambda run input
			execute_lambda_params[ "_refinery" ][ "inline_code" ] = {
				"base_code": inline_execution_code,
				"shared_files": self.json[ "shared_files" ]
			}

		if "debug_id" in self.json:
			execute_lambda_params[ "_refinery" ][ "live_debug" ] = {
				"debug_id": self.json[ "debug_id" ],
				"websocket_uri": self.app_config.get( "LAMBDA_CALLBACK_ENDPOINT" ),
			}

		self.logger( "Executing Lambda '" + lambda_info[ "arn" ] + "'..." )

		lambda_result = yield self.task_spawner.execute_aws_lambda(
			credentials,
			lambda_info[ "arn" ],
			execute_lambda_params
		)

		if "Task timed out after " in lambda_result[ "logs" ]:
			self.logger( "Lambda timed out while being executed!" )
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
			s3_object = yield self.task_spawner.read_from_s3(
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
		except Exception as e:
			self.logger( "Exception occurred while loading temporary Lambda return data: " )
			self.logger( e )
			self.logger( "Raw Lambda return data: " )
			self.logger( lambda_result )

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
		"""
		if self.json[ "language" ] in NOT_SUPPORTED_INLINE_EXECUTION_LANGUAGES:
			self.logger( "Deleting Lambda..." )

			# Now we delete the lambda, don't yield because we don't need to wait
			delete_result = self.task_spawner.delete_aws_lambda(
				credentials,
				random_node_id
			)
		"""

		self.write({
			"success": True,
			"result": lambda_result
		})


class InfraTearDownDependencies:
	@pinject.copy_args_to_public_fields
	def __init__(
			self,
			api_gateway_manager,
			lambda_manager,
			schedule_trigger_manager,
			sns_manager,
			sqs_manager
	):
		pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class InfraTearDown( BaseHandler ):
	dependencies = InfraTearDownDependencies
	api_gateway_manager = None
	lambda_manager = None
	schedule_trigger_manager = None
	sns_manager = None
	sqs_manager = None

	@authenticated
	@gen.coroutine
	def post( self ):
		teardown_nodes = self.json[ "teardown_nodes" ]

		credentials = self.get_authenticated_user_cloud_configuration()

		teardown_operation_results = yield teardown_infrastructure(
			self.api_gateway_manager,
			self.lambda_manager,
			self.schedule_trigger_manager,
			self.sns_manager,
			self.sqs_manager,
			credentials,
			teardown_nodes
		)

		# Delete our logs
		# No need to yield till it completes
		delete_logs(
			self.task_spawner,
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
		self.logger( "Checking for production collisions..." )

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
					self.task_spawner.get_aws_lambda_existence_info(
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
					self.task_spawner.get_cloudwatch_existence_info(
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
					self.task_spawner.get_sqs_existence_info(
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
					self.task_spawner.get_sns_existence_info(
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


class DeployDiagramDependencies:
	@pinject.copy_args_to_public_fields
	def __init__( self, lambda_manager, api_gateway_manager, schedule_trigger_manager, sns_manager, sqs_manager ):
		pass


class DeployDiagram( BaseHandler ):
	dependencies = DeployDiagramDependencies
	lambda_manager = None
	api_gateway_manager = None
	schedule_trigger_manager = None
	sns_manager = None
	sqs_manager = None

	@authenticated
	@disable_on_overdue_payment
	@gen.coroutine
	def post( self ):
		validate_schema( self.json, DEPLOY_DIAGRAM_SCHEMA)

		self.logger( "Deploying diagram to production..." )

		# Ensure user is owner of the project
		if not self.is_owner_of_project( self.json[ "project_id" ] ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have privileges to deploy that!",
			})
			raise gen.Return()

		project_id = self.json[ "project_id" ]
		project_name = self.json[ "project_name" ]
		project_config = self.json[ "project_config" ]

		diagram_data = json.loads( self.json[ "diagram_data" ] )

		credentials = self.get_authenticated_user_cloud_configuration()

		deployment_data = yield deploy_diagram(
			self.task_spawner,
			self.api_gateway_manager,
			credentials,
			project_name,
			project_id,
			diagram_data,
			project_config
		)

		# Check if the deployment failed
		if not deployment_data[ "success" ]:
			self.logger( "We are now rolling back the deployments we've made...", "error" )
			yield teardown_infrastructure(
				self.api_gateway_manager,
				self.lambda_manager,
				self.schedule_trigger_manager,
				self.sns_manager,
				self.sqs_manager,
				credentials,
				deployment_data[ "teardown_nodes_list" ]
			)
			self.logger( "We've completed our rollback, returning an error...", "error" )

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
		self.logger( "Updating database with new project config..." )
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

		aws_console_signin_url = "https://{account_id}.signin.aws.amazon.com/console/?region={region_name}".format(
			account_id=credentials[ "account_id" ],
			region_name=self.app_config.get( "region_name" )
		)

		self.write({
			"success": True,
			"console_credentials": {
				"username": credentials[ "iam_admin_username" ],
				"password": credentials[ "iam_admin_password" ],
				"signin_url": aws_console_signin_url,
			}
		})
