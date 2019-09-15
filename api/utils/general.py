import sys
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