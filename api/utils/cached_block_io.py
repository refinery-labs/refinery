import json

from models.initiate_database import *
from models.cached_block_io import CachedBlockIO
from models.deployments import Deployment

from tornado import gen

from utils.general import logit

@gen.coroutine
def cache_returned_log_items( user_id, credentials, logs_list ):
	"""
	Takes in the log array returned from the /api/v1/logs/executions/get-logs
	endpoint and compares it against the deployment diagram. Once it gets the
	raw block ID from this it stores the cached input/return data in the database.

	[
	  {
	    "log_id": "89938214-0666-41d3-8201-b6a4226843a5",
	    "log_data": {
	      "project_id": "8cb1c5a8-2d87-4abb-ae8d-c9390dbcfe03",
	      "stream_name": "2019/11/03/[$LATEST]41823dd3bba246abbfb73fe680c58883",
	      "memory_limit_in_mb": 768,
	      "initialization_time": 1572819623,
	      "execution_pipeline_id": "784b86f3-5c8f-4cdb-923e-39320714783c",
	      "aws_request_id": "a3a7d9c5-32b1-4dd0-a3f8-14fd19fcaaf9",
	      "name": "Node_810_RFNrnZzib0",
	      "timestamp": 1572819625,
	      "backpack": {},
	      "aws_region": "us-west-2",
	      "group_name": "/aws/lambda/Node_810_RFNrnZzib0",
	      "input_data": "",
	      "program_output": "ayy\nayy2\n",
	      "id": "89938214-0666-41d3-8201-b6a4226843a5",
	      "return_data": "Hello World!",
	      "invoked_function_arn": "arn:aws:lambda:us-west-2:561628006572:function:Node_810_RFNrnZzib0",
	      "type": "SUCCESS",
	      "function_version": "$LATEST",
	      "arn": "arn:aws:lambda:us-west-2:561628006572:function:Node_810_RFNrnZzib0",
	      "function_name": "Node_810_RFNrnZzib0"
	    }
	  }
	]
	"""
	# If there are no logs, there's nothing to cache so quit out
	if len( logs_list ) == 0:
		return

	# Pull project ID from logs
	project_id = logs_list[0][ "log_data" ][ "project_id" ]

	# Pull block ARN from logs
	code_block_arn = logs_list[0][ "log_data" ][ "arn" ]

	# Get the deployment diagram from the database
	dbsession = DBSession()
	latest_deployment = dbsession.query( Deployment ).filter_by(
		aws_account_id=credentials[ "id" ],
		project_id=project_id
	).order_by(
		Deployment.timestamp.desc()
	).first()

	# If there's no match just return here
	# This can happen because previous the aws_account_id wasn't being
	# populated in the `deployments` table.
	if latest_deployment == None:
		return

	deployment_diagram_dict = latest_deployment.to_dict()
	dbsession.close()
	deployment_diagram = deployment_diagram_dict[ "deployment_json" ]

	# Get Code Block ID from diagram JSON
	code_block_id = get_block_id_from_arn(
		deployment_diagram,
		code_block_arn
	)

	# Run through all logs and cache input/return data
	for log_metadata in logs_list:
		log_data = log_metadata[ "log_data" ]

		logit( "Cache input and return data for Code Block '" + code_block_id + "'..." )

		# Cache input data
		cache_block_io_data(
			user_id,
			code_block_id,
			"DEPLOYMENT",
			"INPUT",
			log_data[ "input_data" ]
		)

		# Cache return data
		cache_block_io_data(
			user_id,
			code_block_id,
			"DEPLOYMENT",
			"RETURN",
			log_data[ "return_data" ]
		)

	return

def get_block_id_from_arn( deployment_diagram, block_arn ):
	"""
	Get a block ARN from a deployment diagram.
	"""

	# Search diagram data for the deployed block with matching ARN
	for workflow_state in deployment_diagram[ "workflow_states" ]:
		if workflow_state[ "arn" ] == block_arn:
			return workflow_state[ "id" ]

	# Raise an exception if we got here, means the block didn't exist
	raise Exception( "No block was found in the diagram data with block ARN '" + block_arn + "'!" )

def cache_block_io_data( user_id, code_block_id, origin, io_type, body ):
	logit("Storing block '" + io_type + "' data from '" + origin + "', body: " )
	logit(body)

	"""
	Cache some return data for use later when building block input
	transformations.

	We will only store 10 input and return values at most.
	"""
	dbsession = DBSession()

	new_return_data = CachedBlockIO()
	new_return_data.user_id = user_id
	new_return_data.io_type = io_type
	new_return_data.block_id = code_block_id
	new_return_data.origin = origin

	if type( body ) != str:
		body = json.dumps(
			body,
			indent=4,
			sort_keys=True
		)

	new_return_data.body = body

	dbsession.add( new_return_data )
	dbsession.commit()
	dbsession.close()

	return True

@gen.coroutine
def get_cached_block_data_for_block_id( user_id, code_block_ids, io_type, origin ):
	"""
	This gets the cached block IO data.

	"io_type" and "origin" are optional parameters.
	"""
	db_query_params = {
		"user_id": user_id
	}

	if io_type:
		db_query_params[ "io_type" ] = io_type

	if origin:
		db_query_params[ "origin" ] = origin

	dbsession = DBSession()
	block_io_records_query = dbsession.query( CachedBlockIO ).filter_by(
		**db_query_params
	).filter(
		# List comprehension - sorry about that.
		# This essentially askes "If the block ID matches ANY of the IDs in the code_block_ids list"
		sql_or(
			*[CachedBlockIO.block_id == code_block_id for code_block_id in code_block_ids]
		)		
	).order_by(
		CachedBlockIO.timestamp.desc()
	).limit(25)

	print( block_io_records_query )
	block_io_records = block_io_records_query.all()

	# Convert db records into dicts
	block_io_list = []

	for block_io_record in block_io_records:
		block_io_list.append(
			block_io_record.to_dict()
		)

	dbsession.close()

	return block_io_list