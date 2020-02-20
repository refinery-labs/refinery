import json
import os 

CUSTOMER_IAM_POLICY = ""

def iam_policy_init():
	global CUSTOMER_IAM_POLICY
	file_directory = os.path.dirname(os.path.realpath(__file__))
	policy_path = file_directory + "/../install/refinery-customer-iam-policy.json"

	# Load the default customer IAM policy
	with open( policy_path, "r" ) as file_handler:
		CUSTOMER_IAM_POLICY = json.loads(
			file_handler.read()
		)

iam_policy_init()