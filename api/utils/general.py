import sys
import uuid
import json
import logging

logging.basicConfig(
	stream=sys.stdout,
	level=logging.INFO
)

def attempt_json_decode( input_data ):
	# Try to parse Lambda input as JSON
	try:
		input_data = json.loads(
			input_data
		)
	except:
		pass
	
	return input_data
	
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
	
	logging_func = getattr(
		logging,
		message_type,
		logging.info
	)
	
	logging_func( message )

def split_list_into_chunks( input_list, chunk_size ):
	def split_list( inner_input_list, inner_chunk_size ):
		for i in range(0, len(inner_input_list), inner_chunk_size):  
			yield inner_input_list[i:i + inner_chunk_size] 

	return list(
		split_list(
			input_list,
			chunk_size
		)
	)

def get_random_node_id():
	return "n" + str( uuid.uuid4() ).replace( "-", "" )