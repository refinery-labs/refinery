from utils.general import attempt_json_decode, logit

def parse_websocket_message( input_message ):
	"""
	Returns the dictionary if it's a valid message and
	returns False if it is not.
	"""
	message_contents = attempt_json_decode(
		input_message
	)
	
	# Reject it if it's not a dict
	if type( message_contents ) != dict:
		return False
	
	# Reject it if it doesn't contain a "debug_id"
	if not "debug_id" in message_contents:
		return False
	
	return message_contents