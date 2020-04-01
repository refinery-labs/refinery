import functools
import tornado
import copy
import json
import re

from tornado.concurrent import run_on_executor, futures

from assistants.deployments.sqs import get_sqs_arn_from_url
from utils.general import logit
from tornado import gen

from models.users import User
from models.initiate_database import *
from utils.performance_decorators import emit_runtime_metrics


@gen.coroutine
def get_user_dangling_resources( aws_resource_enumerator, db_session_maker, user_id, credentials ):
	dbsession = db_session_maker()
	user = dbsession.query( User ).filter_by(
		id=str( user_id )
	).first()

	logit( "Pulling all user deployment schemas..." )

	# Pull all of the user's deployment diagrams
	deployment_schemas_list = []

	for project in user.projects:
		for deployment in project.deployments:
			deployment_schemas_list.append(
				json.loads(
					deployment.deployment_json
				)
			)

	dbsession.close()

	logit( "Querying AWS account to enumerate dangling resources..." )

	# Get list of all dangling resources to clear
	dangling_resources = yield aws_resource_enumerator.get_all_dangling_resources(
		credentials,
		deployment_schemas_list
	)

	raise gen.Return( dangling_resources )


def get_arns_from_deployment_diagram( deployment_schema ):
	deployed_arns = []

	for workflow_state in deployment_schema[ "workflow_states" ]:
		if "arn" in workflow_state:
			deployed_arns.append(
				workflow_state[ "arn" ]
			)

	return deployed_arns


def get_arns_from_deployment_diagrams( deployment_schemas_list ):
	all_deployed_arns = []

	for deployment_schema in deployment_schemas_list:
		deployed_arns = get_arns_from_deployment_diagram(
			deployment_schema
		)

		all_deployed_arns = all_deployed_arns + deployed_arns

	return all_deployed_arns


def convert_type_to_teardown_node_type( input_type ):
	"""
	Fix the node type so it matches the format for teardown_nodes.

	Another hack that should be refactored out.
	"""
	if input_type == "sqs":
		return "sqs_queue"
	elif input_type == "sns":
		return "sns_topic"
	elif input_type == "sqs":
		return "sqs_queue"
	elif input_type == "events":
		return "schedule_trigger"

	return input_type


class AwsResourceEnumerator( object ):
	aws_client_factory = None
	aws_cloudwatch_client = None
	logger = None

	@pinject.copy_args_to_public_fields
	def __init__(self, aws_client_factory, aws_cloudwatch_client, logger, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()
	
	@gen.coroutine
	def get_all_dangling_resources( self, credentials, deployment_schemas_list ):
		refinery_managed_arns = get_arns_from_deployment_diagrams(
			deployment_schemas_list
		)

		# First pull a list of all AWS resources under the account
		aws_resources_list = yield self.get_all_aws_resources(
			credentials
		)

		# Reduce it to just a list of Refinery-deployed resources
		refinery_resource_list = []

		# Regex to match deployed resource names
		resource_regex = re.compile(
			"\_RFN[a-zA-Z0-9]{6}\d+"
		)

		for aws_resource_metadata in aws_resources_list:
			if re.search( resource_regex, aws_resource_metadata[ "id" ] ):
				refinery_resource_list.append( aws_resource_metadata )

		# For SQS (edge case) convert URLs to ARNs
		for aws_resource in refinery_resource_list:
			if aws_resource[ "type" ] == "sqs":
				aws_resource[ "id" ] = get_sqs_arn_from_url(
					aws_resource[ "id" ]
				)

			aws_resource[ "type" ] = convert_type_to_teardown_node_type(
				aws_resource[ "type" ]
			)

		dangling_arns = []

		# Remove all of the resources that are in known-deploys
		for refinery_resource in refinery_resource_list:
			if not ( refinery_resource[ "id" ] in refinery_managed_arns ):
				dangling_arns.append(
					refinery_resource
				)

		raise gen.Return( dangling_arns )

	@gen.coroutine
	def get_all_aws_resources( self, credentials ):
		"""
		Pulls a list of all AWS resources which were deployed by Refinery
		but are no longer tracked by any deployment diagram (meaning they
		probably should be deleted).
		"""

		# List of functions to enumerate AWS resources
		resource_enumeration_inputs = [
			{
				"client_type": "lambda",
				"list_function": "list_functions",
				"marker_name": "Marker",
				"next_marker_name": "NextMarker",
				"result_key": "Functions",
				"arn_key": "FunctionArn",
				"extra_options": {
					"MaxItems": 50
				}
			},
			{
				"client_type": "sns",
				"list_function": "list_topics",
				"marker_name": "NextToken",
				"next_marker_name": "NextToken",
				"result_key": "Topics",
				"arn_key": "TopicArn",
				"extra_options": {}
			},
			{
				"client_type": "sqs",
				"list_function": "list_queues",
				"marker_name": "",
				"next_marker_name": "",
				"result_key": "QueueUrls",
				"arn_key": "",
				"extra_options": {}
			},
			{
				"client_type": "events",
				"list_function": "list_rules",
				"marker_name": "NextToken",
				"next_marker_name": "NextToken",
				"result_key": "Rules",
				"arn_key": "Arn",
				"extra_options": {
					"Limit": 100
				}
			}
		]

		resources_list = []
		resource_futures = []

		for resource_enumeration_input in resource_enumeration_inputs:
			enumeration_function_with_args = functools.partial(
				self.iterate_list_pages,
				credentials,
				**resource_enumeration_input
			)

			resource_futures.append(
				enumeration_function_with_args()
			)

		enumerated_resource_lists = yield resource_futures

		all_resources_list = []

		for enumerated_resource in enumerated_resource_lists:
			all_resources_list = all_resources_list + enumerated_resource

		raise gen.Return( all_resources_list )

	@run_on_executor
	@emit_runtime_metrics( "dangling_resources__iterate_list_pages" )
	def iterate_list_pages( self, credentials, client_type, list_function, marker_name, next_marker_name, result_key, arn_key, extra_options ):
		"""
		client_type: Type of resource being listed (e.g. "sns", "lambda")
		list_function: Boto function call (e.g. "list_functions" for Lambda) that lists the resource
		marker_name: The object name of the parameter passed to the list function to get the next page of results.
		result_key: What key in the response dict has the list of resources
		arn_key: In the list of resources in the response, what key holds the ARN.
		extra_options: Extra parameters to send to list function
		"""
		aws_client = self.aws_client_factory.get_aws_client(
			client_type,
			credentials
		)

		more_results = True
		next_token = False
		max_pages = 100

		arn_list = []

		while more_results:
			options = copy.copy(extra_options)
			max_pages = max_pages - 1

			if max_pages <= 0:
				break

			if next_token:
				options[ marker_name ] = next_token

			list_function_to_call = getattr(
				aws_client,
				list_function
			)

			logit( "Grabbing another page of results for '" + client_type + "'..." )
			list_resources_response = list_function_to_call(
				**options
			)

			next_token = False
			if next_marker_name in list_resources_response:
				next_token = list_resources_response[ next_marker_name ]

			# List comprehension, which I normally hate but eh.
			if arn_key and arn_key != "":
				resource_arns = [ resource_dict[ arn_key ] for resource_dict in list_resources_response[ result_key ] ]
				arn_list = resource_arns + arn_list
			else:
				arn_list = arn_list + list_resources_response[ result_key ]

			if next_token == False:
				break

		return_list = []

		for arn in arn_list:
			return_list.append({
				"id": arn,
				"type": client_type
			})

		return return_list

	@run_on_executor
	@emit_runtime_metrics( "dangling_resources__get_all_sqs_queues" )
	def get_all_sqs_queues( self, credentials ):
		sqs_client = self.aws_client_factory.get_aws_client(
			"sqs",
			credentials
		)

		list_queues_response = sqs_client.list_queues()

		return_list = []

		for queue_url in list_queues_response[ "QueueUrls" ]:
			return_list.append({
				"id": queue_url,
				"type": "sqs"
			})

		return return_list
