import time

def get_user_free_trial_information( input_user ):
	return_data = {
		"trial_end_timestamp": 0,
		"trial_started_timestamp": 0,
		"trial_over": False,
		"is_using_trial": True,
	}

	# If the user has a payment method on file they can't be using the
	# free trial.
	if input_user.has_valid_payment_method_on_file == True:
		return_data[ "is_using_trial" ] = False
		return_data[ "trial_over" ] = True

	# Calculate when the trial is over
	trial_length_in_seconds = ( 60 * 60 * 24 * 14 )
	return_data[ "trial_started_timestamp" ] = input_user.timestamp
	return_data[ "trial_end_timestamp" ] = input_user.timestamp + trial_length_in_seconds

	# Calculate if the user is past their free trial
	current_timestamp = int( time.time() )

	# Calculate time since user sign up
	seconds_since_signup = current_timestamp - input_user.timestamp

	# If it's been over 14 days since signup the user
	# has exhausted their free trial
	if seconds_since_signup > trial_length_in_seconds:
		return_data[ "trial_over" ] = True

	return return_data

