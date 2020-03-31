"""
TODO when local tasks get refactored this should probably be refactored too
"""
import datetime
import math

from models import AWSAccount, Organization


def get_current_month_start_and_end_date_strings():
	"""
	Returns the start date string of this month and
	the start date of the next month for pulling AWS
	billing for the current month.
	"""
	# Get tomorrow date
	today_date = datetime.date.today()
	tomorrow_date = datetime.date.today() + datetime.timedelta( days=1 )
	start_date = tomorrow_date

	# We could potentially be on the last day of the month
	# making tomorrow the next month! Check for this case.
	# If it's the case then we'll just set the start date to today
	if tomorrow_date.month == today_date.month:
		start_date = today_date

	# Get first day of next month
	current_month_num = today_date.month
	current_year_num = today_date.year
	next_month_num = current_month_num + 1

	# Check if we're on the last month
	# If so the next month number is 1
	# and we should add 1 to the year
	if current_month_num == 12:
		next_month_num = 1
		current_year_num = current_year_num + 1

	next_month_start_date = datetime.date(
		current_year_num,
		next_month_num,
		1
	)

	return {
		"current_date": tomorrow_date.strftime( "%Y-%m-%d" ),
		"month_start_date": tomorrow_date.strftime( "%Y-%m-01" ),
		"next_month_first_day": next_month_start_date.strftime( "%Y-%m-%d" ),
	}


def is_organization_first_month( db_session_maker, aws_account_id ):
	# Pull the relevant organization from the database to check
	# how old the account is to know if the first-month's base fee should be applied.
	dbsession = db_session_maker()
	aws_account = dbsession.query( AWSAccount ).filter_by(
		account_id=aws_account_id
	).first()
	organization = dbsession.query( Organization ).filter_by(
		id=aws_account.organization_id
	).first()
	organization_dict = organization.to_dict()
	dbsession.close()

	account_creation_dt = datetime.datetime.fromtimestamp(
		organization.timestamp
	)

	current_datetime = datetime.datetime.now()

	if account_creation_dt > ( current_datetime - datetime.timedelta( days=40 ) ):
		return True

	return False


def get_billing_rounded_float( input_price_float ):
	"""
	This is used because Stripe only allows you to charge line
	items in cents. Meaning that some rounding will occur on the
	final line items on the bill. AWS returns us lengthy-floats which
	means that the conversion will have to be done in both the invoice
	billing and the bill calculation endpoints the same way. We also have
	to do this in a safe round up way that won't accidentally under-bill
	our customers.

	This endpoint basically converts the AWS float into cents, rounds it,
	and then converts it back to a float rounded appropriately to two digits
	and returns the float again. All billing code should use this to ensure
	consistency in what the user sees from a billing point of view.
	"""
	# Special case is when the input float is 0
	if input_price_float == 0:
		return float( 0.00 )

	# Round float UP TO second digit
	# Meaning 10.015 becomes 10.02
	# and 10.012 becomes 10.02
	rounded_up_float = (
			math.ceil(
				input_price_float * 100
			) / 100
	)

	return rounded_up_float
