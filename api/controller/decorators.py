"""
Decorators used by controllers to enforce endpoint preconditions
"""
import time


def authenticated( func ):
	"""
	Decorator to ensure the user is currently authenticated.

	If the user is not, the response will be:
	{
		"success": false,
		"code": "AUTH_REQUIRED",
		"msg": "...",
	}
	"""
	def wrapper( *args, **kwargs ):
		self_reference = args[0]

		authenticated_user = self_reference.get_authenticated_user()

		if authenticated_user is None:
			self_reference.write({
				"success": False,
				"code": "AUTH_REQUIRED",
				"msg": "You must be authenticated to do this!",
			})
			return

		return func( *args, **kwargs )
	return wrapper

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


def disable_on_overdue_payment( func ):
	"""
	Decorator to disable specific endpoints if the user
	is in collections and needs to settle up their bill.

	If the user is not, the response will be:
	{
		"success": false,
		"code": "ORGANIZATION_UNSETTLED_BILLS",
		"msg": "...",
	}
	"""
	def wrapper( *args, **kwargs ):
		self_reference = args[0]

		# Pull the authenticated user
		authenticated_user = self_reference.get_authenticated_user()

		# Pull the user's org to see if any payments are overdue
		authenticated_user_org = authenticated_user.organization

		if authenticated_user_org.payments_overdue:
			self_reference.write({
				"success": False,
				"code": "ORGANIZATION_UNSETTLED_BILLS",
				"msg": "This organization has an unsettled bill which is overdue for payment. This action can not be performed until the outstanding bills have been paid.",
			})
			return

		# Check if the user is on a free trial and if the free trial is over
		trial_info = get_user_free_trial_information( authenticated_user )

		if trial_info[ "is_using_trial" ] and trial_info[ "trial_over" ]:
			self_reference.write({
				"success": False,
				"code": "USER_FREE_TRIAL_ENDED",
				"msg": "Your free trial has ended, you must supply a payment method in order to perform this action.",
			})
			return

		return func( *args, **kwargs )
	return wrapper
