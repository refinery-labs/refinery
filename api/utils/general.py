import json

def attempt_json_decode( input_data ):
	# Try to parse Lambda input as JSON
	try:
		input_data = json.loads(
			input_data
		)
	except:
		pass
	
	return input_data