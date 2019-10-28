from tornado import gen

from utils.general import logit

from utils.deployments.sqs import sqs_manager
from utils.deployments.sns import sns_manager
from utils.deployments.awslambda import lambda_manager
from utils.deployments.schedule_trigger import schedule_trigger_manager
from utils.deployments.api_gateway import api_gateway_manager, strip_api_gateway

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

	# Add an ID and "name" to nodes if not set, they are not technically
	# required and are a remnant of the old code.
	# This all needs to be refactored, but that's a much larger undertaking.
	for teardown_node in teardown_nodes:
		if not ( "name" in teardown_node ):
			teardown_node[ "name" ] = teardown_node[ "id" ]

		if not ( "arn" in teardown_node ):
			teardown_node[ "arn" ] = teardown_node[ "id" ]
	
	for teardown_node in teardown_nodes:
		# Skip if the node doesn't exist
		# TODO move this client side, it's silly here.
		if "exists" in teardown_node and teardown_node[ "exists" ] == False:
			continue
		
		if teardown_node[ "type" ] == "lambda" or teardown_node[ "type" ] == "api_endpoint":
			teardown_operation_futures.append(
				lambda_manager.delete_lambda(
					credentials,
					teardown_node[ "id" ],
					teardown_node[ "type" ],
					teardown_node[ "name" ],
					teardown_node[ "arn" ],
				)
			)
		elif teardown_node[ "type" ] == "sns_topic":
			teardown_operation_futures.append(
				sns_manager.delete_sns_topic(
					credentials,
					teardown_node[ "id" ],
					teardown_node[ "type" ],
					teardown_node[ "name" ],
					teardown_node[ "arn" ],
				)
			)
		elif teardown_node[ "type" ] == "sqs_queue":
			teardown_operation_futures.append(
				sqs_manager.delete_sqs_queue(
					credentials,
					teardown_node[ "id" ],
					teardown_node[ "type" ],
					teardown_node[ "name" ],
					teardown_node[ "arn" ],
				)
			)
		elif teardown_node[ "type" ] == "schedule_trigger" or teardown_node[ "type" ] == "warmer_trigger":
			teardown_operation_futures.append(
				schedule_trigger_manager.delete_schedule_trigger(
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