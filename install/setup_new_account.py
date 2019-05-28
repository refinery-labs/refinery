#!/usr/bin/env python2
import botocore.exceptions
import shortuuid
import boto3
import yaml
import json
import time
import os, sys, string, struct

# Prefix for all managed Refinery customer AWS accounts
REFINERY_AWS_ACCOUNT_EMAIL_PREFIX = "aws-"

# The @ email for all managed Refinery customer AWS accounts
REFINERY_AWS_ACCOUNT_EMAIL_SUFFIX = "@mail.refineryusercontent.com"

try:
	with open( "config.yml", "r" ) as file_handler:
		aws_credentials_config = yaml.safe_load(
			file_handler.read()
		)
except:
	print( "No config.yml present, it's required to use this tool. Please create one with the credentials of the root AWS account." )
	exit()
	
def pprint( input_dict ):
	try:
		print( json.dumps( input_dict, sort_keys=True, indent=4, separators=( ",", ": " ) ) )
	except:
		print( input_dict )
	
def load_json_file( file_path ):
	file_contents = False
	with open( file_path, "r" ) as file_handler:
		file_contents = json.loads( file_handler.read() )
	return file_contents
	
def get_urand_password( length ):
    symbols = string.ascii_letters + string.digits
    return "".join([symbols[x * len(symbols) / 256] for x in struct.unpack("%dB" % (length,), os.urandom(length))])

def create_aws_sub_account( refinery_aws_account_id, email ):
	account_name = "Refinery Customer Account " + refinery_aws_account_id
	
	organizations_client = boto3.client(
		"organizations",
		aws_access_key_id=aws_credentials_config[ "aws_access_key_id" ],
		aws_secret_access_key=aws_credentials_config[ "aws_secret_access_key" ],
		region_name=aws_credentials_config[ "aws_region" ],
	)
	
	response = organizations_client.create_account(
		Email=email,
		RoleName="DO_NOT_DELETE_REFINERY_SYSTEM_ACCOUNT",
		AccountName=account_name,
		IamUserAccessToBilling="DENY"
	)
	account_status_data = response[ "CreateAccountStatus" ]
	create_account_id = account_status_data[ "Id" ]
	
	# Loop while the account is being created
	while True:
		if account_status_data[ "State" ] == "SUCCEEDED" and "AccountId" in account_status_data:
			return {
				"account_name": account_name,
				"account_id": account_status_data[ "AccountId" ],
			}
			
		if account_status_data[ "State" ] == "FAILED":
			print( "[ ERROR ] The account creation has failed!" )
			print( "Full account creation response is the following: " )
			pprint( account_status_data )
			return False
		
		print( "[ STATUS ] Current AWS account creation status is '" + account_status_data[ "State" ] + "', waiting 5 seconds before checking again..." )
		time.sleep( 5 )
		
		# Poll AWS again to see if the account creation has progressed
		response = organizations_client.describe_create_account_status(
			CreateAccountRequestId=create_account_id
		)
		account_status_data = response[ "CreateAccountStatus" ]
	
def get_assume_role_credentials( role_arn, session_lifetime ):
	# Session lifetime must be a minimum of 15 minutes
	# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html#STS.Client.assume_role
	min_session_lifetime_seconds = 900
	if session_lifetime < min_session_lifetime_seconds:
		session_lifetime = min_session_lifetime_seconds
	
	sts_client = boto3.client(
		"sts",
		aws_access_key_id=aws_credentials_config[ "aws_access_key_id" ],
		aws_secret_access_key=aws_credentials_config[ "aws_secret_access_key" ],
		region_name=aws_credentials_config[ "aws_region" ],
	)
	
	role_session_name = "Refinery-Managed-Account-Support-" + get_urand_password( 12 )
	
	response = sts_client.assume_role(
		RoleArn=role_arn,
		RoleSessionName=role_session_name,
		DurationSeconds=session_lifetime
	)
	
	return {
		"access_key_id": response[ "Credentials" ][ "AccessKeyId" ],
		"secret_access_key": response[ "Credentials" ][ "SecretAccessKey" ],
		"session_token": response[ "Credentials" ][ "SessionToken" ],
		"expiration_date": response[ "Credentials" ][ "Expiration" ],
		"assumed_role_id": response[ "AssumedRoleUser" ][ "AssumedRoleId" ],
		"role_session_name": role_session_name,
		"arn": response[ "AssumedRoleUser" ][ "Arn" ],
	}
	
def create_new_console_user( access_key_id, secret_access_key, session_token, username, password ):
	# Create a Boto3 session with the assumed role credentials
	# This allows us to create a client which will be authenticated
	# as the account we assumed the role of.
	iam_session = boto3.Session(
		aws_access_key_id=access_key_id,
		aws_secret_access_key=secret_access_key,
		aws_session_token=session_token
	)
	
	# IAM client spawned from the assumed role session
	iam_client = iam_session.client( "iam" )
	
	# Create an IAM user
	create_user_response = iam_client.create_user(
		UserName=username
	)
	
	# Create IAM policy for the user
	create_policy_response = iam_client.create_policy(
		PolicyName="RefineryCustomerPolicy",
		PolicyDocument=json.dumps(
			load_json_file(
				"refinery-customer-iam-policy.json"
			)
		),
		Description="Refinery Labs managed AWS customer account policy."
	)
	
	# Attaches limited access policy to the AWS account to scope
	# down the permissions the Refinery customer can perform in
	# the AWS console.
	attach_policy_response = iam_client.attach_user_policy(
		UserName=username,
		PolicyArn=create_policy_response[ "Policy" ][ "Arn" ]
	)
	
	# Allow the IAM user to access the account through the console
	create_login_profile_response = iam_client.create_login_profile(
		UserName=username,
		Password=password,
		PasswordResetRequired=False,
	)
	
	return {
		"username": username,
		"password": password,
		"arn": create_user_response[ "User" ][ "Arn" ]
	}
	
def create_new_refinery_aws_account():
	print( "[ STATUS ] Starting Refinery Customer AWS account creation tool..." )
	
	# Used to keep all of the account details in one place
	# for later insert into the database
	account_details = {}
	
	# Create a unique ID for the Refinery AWS account
	account_details[ "id" ] = shortuuid.ShortUUID().random(
		length=16
	).lower()
	
	# Generate and set some secrets
	account_details[ "refinery_customer_aws_console_username" ] = "refinery-customer-" + account_details[ "id" ]
	account_details[ "refinery_customer_aws_console_password" ] = get_urand_password( 128 )
	account_details[ "s3_bucket_suffix" ] = str( get_urand_password( 32 ) ).lower()
	account_details[ "redis_password" ] = get_urand_password( 64 )
	account_details[ "redis_prefix" ] = get_urand_password( 40 )
	
	# Create unique email for the account
	# All emails with this "aws-" prefix are captured via Mailgun
	# and are routed to the "refinery-aws-accounts@refinerylabs.io Google Group
	account_details[ "email" ] = REFINERY_AWS_ACCOUNT_EMAIL_PREFIX + account_details[ "id" ] + REFINERY_AWS_ACCOUNT_EMAIL_SUFFIX
	
	print( "[ STATUS ] Creating AWS sub-account with email " + account_details[ "email" ] )
	
	# Create sub-AWS account
	account_creation_response = create_aws_sub_account(
		account_details[ "id" ],
		account_details[ "email" ],
	)
	
	if account_creation_response == False:
		raise Exception( "Account creation failed, quitting out!" )
	
	account_details[ "account_name" ] = account_creation_response[ "account_name" ]
	account_details[ "account_id" ] = account_creation_response[ "account_id" ]
	
	print( "[ STATUS ] Sub-account created! AWS account ID is " + account_details[ "account_id" ] + " and the name is '" + account_details[ "account_name" ] + "'" )
	
	# Generate ARN for the sub-account AWS administrator role
	sub_account_admin_role_arn = "arn:aws:iam::" + str( account_details[ "account_id" ] ) + ":role/DO_NOT_DELETE_REFINERY_SYSTEM_ACCOUNT"
	
	print( "[ STATUS ] Sub-account role ARN is '" + sub_account_admin_role_arn + "'." )
	
	assumed_role_credentials = {}
	
	while True:
		print( "[ STATUS ] Attempting to assume the sub-account's administrator role..." )
		
		try:
			# We then assume the administrator role for the sub-account we created
			assumed_role_credentials = get_assume_role_credentials(
				sub_account_admin_role_arn,
				3600 # One hour - TODO CHANGEME
			)
			break
		except botocore.exceptions.ClientError as boto_error:
			# If it's not an AccessDenied exception it's not what we except so we re-raise
			if boto_error.response[ "Error" ][ "Code" ] != "AccessDenied":
				raise
			
			# Otherwise it's what we accept and we just need to wait.
			print( "[ STATUS ] Got an Access Denied error, role is likely not propogated yet. Trying again in 5 seconds..." )
			time.sleep( 5 )
	
	print( "[ STATUS ] Successfully assumed the sub-account's administrator role." )
	print( "[ STATUS ] Minting a new AWS Console User account for the customer to use..." )
	
	# Using the credentials from the assumed role we mint an IAM console
	# user for Refinery customers to use to log into their managed AWS account.
	create_console_user_results = create_new_console_user(
		assumed_role_credentials[ "access_key_id" ],
		assumed_role_credentials[ "secret_access_key" ],
		assumed_role_credentials[ "session_token" ],
		account_details[ "refinery_customer_aws_console_username" ],
		account_details[ "refinery_customer_aws_console_password" ]
	)
	
	print( "[ STATUS ] Successfully minted a console user account!" )
	print( "[ STATUS ] Writing Terraform input variables to file..." )
	
	# Write out the terraform configuration data
	terraform_configuration_data = {
		"session_token": assumed_role_credentials[ "session_token" ],
		"role_session_name": assumed_role_credentials[ "role_session_name" ],
		"assume_role_arn": sub_account_admin_role_arn,
		"access_key": assumed_role_credentials[ "access_key_id" ],
		"secret_key": assumed_role_credentials[ "secret_access_key" ],
		"region": aws_credentials_config[ "aws_region" ],
		"s3_bucket_suffix": account_details[ "s3_bucket_suffix" ],
		"redis_secrets": {
			"password": account_details[ "redis_password" ],
			"secret_prefix": account_details[ "redis_prefix" ],
		}
	}
	
	# Write configuration data to a file for Terraform to use.
	with open( "refinery-customer-aws-config.json", "w" ) as file_handler:
		file_handler.write(
			json.dumps(
				terraform_configuration_data
			)
		)
		
	print( "[ STATUS ] Terraform input variables successfully written to disk. " )
	print( "[ SUCCESS ] AWS account generation is complete!")

create_new_refinery_aws_account()