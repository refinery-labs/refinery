import traceback
import functools
import tornado
import boto3
import copy
import time
import re

from tornado.concurrent import run_on_executor, futures
from utils.aws_client import get_aws_client, STS_CLIENT
from utils.general import logit
from tornado import gen

class AWSResourceEnumerator(object):
	def __init__(self, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()
	
	@gen.coroutine
	def get_all_dangling_resources( self, credentials ):
		# First pull a list of all AWS resources under the account
		aws_resources_list = yield self.get_all_aws_resources(
			credentials
		)

		# Reduce it to just a list of Refinery-deployed resources
		refinery_resource_list = []

		resource_regex = re.compile(
			"\_RFN[a-zA-Z0-9]{6}\d+"
		)

		for aws_resource_metadata in aws_resources_list:
			if re.search( resource_regex, aws_resource_metadata[ "id" ] ):
				refinery_resource_list.append( aws_resource_metadata )

		# Remove all of the resources that are in known-deploys

		# The remaining list is just the dangling ones that can be deleted.

		raise gen.Return( refinery_resource_list )

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
	def iterate_list_pages( self, credentials, client_type, list_function, marker_name, next_marker_name, result_key, arn_key, extra_options ):
		"""
		client_type: Type of resource being listed (e.g. "sns", "lambda")
		list_function: Boto function call (e.g. "list_functions" for Lambda) that lists the resource
		marker_name: The object name of the parameter passed to the list function to get the next page of results.
		result_key: What key in the response dict has the list of resources
		arn_key: In the list of resources in the response, what key holds the ARN.
		extra_options: Extra parameters to send to list function
		"""
		aws_client = get_aws_client(
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
	def get_all_sqs_queues( self, credentials ):
		sqs_client = get_aws_client(
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

aws_resource_enumerator = AWSResourceEnumerator()