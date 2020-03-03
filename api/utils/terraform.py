import os
import json
import uuid
import copy
import shutil
import tornado
import pystache
import subprocess

from os import listdir
from tornado import gen
from os.path import isfile, join
from utils.general import logit
from tornado.concurrent import run_on_executor, futures
from pyconstants.email_templates import EMAIL_TEMPLATES

from utils.base_spawner import BaseSpawner
from utils.free_tier import usage_spawner, free_tier_freezer
from utils.general import get_urand_password
from utils.aws_client import get_aws_client, STS_CLIENT
from utils.aws_account_management.preterraform import preterraform_manager
from utils.emails import EmailSpawner, email_spawner
from models.users import User, RefineryUserTier
from models.initiate_database import DBSession
from models.aws_accounts import AWSAccount
from models.terraform_state_versions import TerraformStateVersion

class TerraformSpawner(BaseSpawner):
	@run_on_executor
	def terraform_update_aws_account( self, current_aws_account_dict, aws_account_status ):		
		logit( "Kicking off terraform set-up for AWS account '" + current_aws_account_dict[ "account_id" ] + "'..." )

		dbsession = DBSession()
		current_aws_account = dbsession.query( AWSAccount ).filter(
			AWSAccount.account_id == current_aws_account_dict[ "account_id" ],
		).first()

		try:
			account_provisioning_details = TerraformSpawner._terraform_configure_aws_account(
				current_aws_account_dict
			)
			
			# Update the AWS account with this new information
			current_aws_account.redis_hostname = account_provisioning_details[ "redis_hostname" ]
			current_aws_account.terraform_state = account_provisioning_details[ "terraform_state" ]
			current_aws_account.ssh_public_key = account_provisioning_details[ "ssh_public_key" ]
			current_aws_account.ssh_private_key = account_provisioning_details[ "ssh_private_key" ]
			current_aws_account.aws_account_status = aws_account_status
			
			# Create a new terraform state version
			terraform_state_version = TerraformStateVersion()
			terraform_state_version.terraform_state = account_provisioning_details[ "terraform_state" ]
			current_aws_account.terraform_state_versions.append(
				terraform_state_version
			)
		except Exception as e:
			logit( "An error occurred while provision AWS account '" + current_aws_account_dict["account_id"] + "' with terraform!", "error" )
			logit( e )
			logit( "Marking the account as 'CORRUPT'..." )
			
			# Mark the account as corrupt since the provisioning failed.
			current_aws_account.aws_account_status = "CORRUPT"
		
		logit( "Commiting new account state of '" + current_aws_account.aws_account_status + "' to database..." )
		dbsession.add(current_aws_account)
		dbsession.commit()

	@run_on_executor
	def terraform_configure_aws_account( self, aws_account_dict ):
		return TerraformSpawner._terraform_configure_aws_account(
			aws_account_dict
		)
		
	@run_on_executor
	def write_terraform_base_files( self, aws_account_dict ):
		return TerraformSpawner._write_terraform_base_files(
			aws_account_dict
		)
		
	@staticmethod
	def _write_terraform_base_files( aws_account_dict ):
		# Create a temporary working directory for the work.
		# Even if there's some exception thrown during the process
		# we will still delete the underlying state.
		temporary_dir = "/tmp/" + str( uuid.uuid4() ) + "/"
		
		result = False
		
		terraform_configuration_data = {}
		
		try:
			# Recursively copy files to the directory
			shutil.copytree(
				"/work/install/",
				temporary_dir
			)
			
			terraform_configuration_data = TerraformSpawner.__write_terraform_base_files(
				aws_account_dict,
				temporary_dir
			)

			# Delete all paid-tier files if the user is free-tier
			# This will ensure the deploy matches the user's tier.

			# Get files in temporary directory
			temporary_dir_files = [f for f in listdir(temporary_dir) if isfile(join(temporary_dir, f))]

			# Pull the account tier (paid/free)
			is_free_tier = usage_spawner._is_free_tier_account(
				aws_account_dict
			)

			# Set appropriate prefix to delete depending on if the account
			# is on the free-tier or not.
			# For example:
			# Delete all files starting with 'PAID-' if we're the free-tier
			# Delete all files starting with 'FREE-' if we're the paid-tier
			deletion_prefix = "PAID-" if is_free_tier else "FREE-"

			print( "Deletion prefix is " + deletion_prefix )

			# Delete the appropriate files with the specified prefix
			for temporary_dir_file in temporary_dir_files:
				if temporary_dir_file.startswith( deletion_prefix ):
					file_to_delete = temporary_dir + temporary_dir_file
					print( "Deleting '" + file_to_delete + "'...")
					os.remove(
						file_to_delete
					)

		except Exception as e:
			logit( "An exception occurred while writing terraform base files for AWS account ID " + aws_account_dict[ "account_id" ] )
			logit( e )
			
			# Delete the temporary directory reguardless.
			shutil.rmtree( temporary_dir )
			
			raise
		
		return terraform_configuration_data
	
	@staticmethod
	def __write_terraform_base_files( aws_account_data, base_dir ):
		logit( "Setting up the base Terraform files (AWS Acc. ID '" + aws_account_data[ "account_id" ] + "')..." )
		
		# Get some temporary assume role credentials for the account
		assumed_role_credentials = TerraformSpawner._get_assume_role_credentials(
			str( aws_account_data[ "account_id" ] ),
			3600 # One hour - TODO CHANGEME
		)
		
		sub_account_admin_role_arn = "arn:aws:iam::" + str( aws_account_data[ "account_id" ] ) + ":role/" + os.environ.get( "customer_aws_admin_assume_role" )
		
		# Write out the terraform configuration data
		terraform_configuration_data = {
			"session_token": assumed_role_credentials[ "session_token" ],
			"role_session_name": assumed_role_credentials[ "role_session_name" ],
			"assume_role_arn": sub_account_admin_role_arn,
			"access_key": assumed_role_credentials[ "access_key_id" ],
			"secret_key": assumed_role_credentials[ "secret_access_key" ],
			"region": os.environ.get( "region_name" ),
			"s3_bucket_suffix": aws_account_data[ "s3_bucket_suffix" ],
			"redis_secrets": {
				"password": aws_account_data[ "redis_password" ],
				"secret_prefix": aws_account_data[ "redis_secret_prefix" ],
			}
		}
		
		logit( "Writing Terraform input variables to file..." )
		
		# Write configuration data to a file for Terraform to use.
		with open( base_dir + "customer_config.json", "w" ) as file_handler:
			file_handler.write(
				json.dumps(
					terraform_configuration_data
				)
			)
			
		# Write the latest terraform state to terraform.tfstate
		# If we have any state at all.
		if aws_account_data[ "terraform_state" ] != "":
			# First we write the current version to the database as a version to keep track
			
			terraform_state_file_path = base_dir + "terraform.tfstate"
			
			logit( "A previous terraform state file exists! Writing it to '" + terraform_state_file_path + "'..." )
			
			with open( terraform_state_file_path, "w" ) as file_handler:
				file_handler.write(
					aws_account_data[ "terraform_state" ]
				)
			
		logit( "The base terraform files have been created successfully at " + base_dir )
		
		terraform_configuration_data[ "base_dir" ] = base_dir
		
		return terraform_configuration_data
		
	@run_on_executor
	def terraform_apply( self, aws_account_data ):
		"""
		This applies the latest terraform config to an account.
		
		THIS IS DANGEROUS, MAKE SURE YOU DID A FLEET TERRAFORM PLAN
		FIRST. NO EXCUSES, THIS IS ONE OF THE FEW WAYS TO BREAK PROD
		FOR OUR CUSTOMERS.
		
		-mandatory
		"""
		return TerraformSpawner._terraform_apply(
			aws_account_data
		)
	
	@staticmethod
	def _terraform_apply( aws_account_data ):
		logit( "Ensuring existence of ECS service-linked role before continuing with terraform apply..." )
		preterraform_manager._ensure_ecs_service_linked_role_exists(
			aws_account_data
		)

		# The return data
		return_data = {
			"success": True,
			"stdout": "",
			"stderr": "",
			"original_tfstate": str(
				copy.copy(
					aws_account_data[ "terraform_state" ]
				)
			),
			"new_tfstate": "",
		}
		
		terraform_configuration_data = TerraformSpawner._write_terraform_base_files(
			aws_account_data
		)
		temporary_directory = terraform_configuration_data[ "base_dir" ]
		
		try:
			logit( "Performing 'terraform apply' to AWS Account " + aws_account_data[ "account_id" ] + "..." )
			
			# Terraform plan
			process_handler = subprocess.Popen(
				[
					temporary_directory + "terraform",
					"apply",
					"-auto-approve",
					"-var-file",
					temporary_directory + "customer_config.json",
				],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False,
				universal_newlines=True,
				cwd=temporary_directory,
			)
			process_stdout, process_stderr = process_handler.communicate()
			return_data[ "stdout" ] = process_stdout
			return_data[ "stderr" ] = process_stderr
			
			# Pull the latest terraform state and return it
			# We need to do this regardless of if an error occurred.
			with open( temporary_directory + "terraform.tfstate", "r" ) as file_handler:
				return_data[ "new_tfstate" ] = file_handler.read()
			
			if process_stderr.strip() != "":
				logit( "The 'terraform apply' has failed!", "error" )
				sys.stderr.write( process_stderr )
				sys.stderr.write( process_stdout )
				
				# Alert us of the provisioning error so we can response to it
				TerraformSpawner.send_terraform_provisioning_error(
					aws_account_data[ "account_id" ],
					str( process_stderr )
				)
				
				return_data[ "success" ] = False
		finally:
			# Ensure we clear the temporary directory no matter what
			shutil.rmtree( temporary_directory )
		
		logit( "'terraform apply' completed, returning results..." )
		
		return return_data
	
	@run_on_executor
	def terraform_plan( self, aws_account_data ):
		"""
		This does a terraform plan to an account and sends an email
		with the results. This allows us to see the impact of a new
		terraform change before we roll it out across our customer's
		AWS accounts.
		"""
		return TerraformSpawner._terraform_plan(
			aws_account_data
		)
	
	@staticmethod
	def _terraform_plan( aws_account_data ):
		terraform_configuration_data = TerraformSpawner._write_terraform_base_files(
			aws_account_data
		)
		temporary_directory = terraform_configuration_data[ "base_dir" ]
		
		try:
			logit( "Performing 'terraform plan' to AWS account " + aws_account_data[ "account_id" ] + "..." )
			
			# Terraform plan
			process_handler = subprocess.Popen(
				[
					temporary_directory + "terraform",
					"plan",
					"-var-file",
					temporary_directory + "customer_config.json",
				],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False,
				universal_newlines=True,
				cwd=temporary_directory,
			)
			process_stdout, process_stderr = process_handler.communicate()
			
			if process_stderr.strip() != "":
				logit( "The 'terraform plan' has failed!", "error" )
				sys.stderr.write( process_stderr )
				sys.stderr.write( process_stdout )
				
				raise Exception( "Terraform plan failed." )
		finally:
			# Ensure we clear the temporary directory no matter what
			shutil.rmtree( temporary_directory )
		
		logit( "Terraform plan completed successfully, returning output." )
		return process_stdout
		
	@staticmethod
	def _terraform_configure_aws_account( aws_account_data ):
		logit( "Ensuring existence of ECS service-linked role before continuing with AWS account configuration..." )
		preterraform_manager._ensure_ecs_service_linked_role_exists(
			aws_account_data
		)

		terraform_configuration_data = TerraformSpawner._write_terraform_base_files(
			aws_account_data
		)
		base_dir = terraform_configuration_data[ "base_dir" ]
		
		try:
			logit( "Setting up AWS account with terraform (AWS Acc. ID '" + aws_account_data[ "account_id" ] + "')..." )
			
			# Terraform apply
			process_handler = subprocess.Popen(
				[
					base_dir + "terraform",
					"apply",
					"-auto-approve",
					"-var-file",
					base_dir + "customer_config.json",
				],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False,
				universal_newlines=True,
				cwd=base_dir,
			)
			process_stdout, process_stderr = process_handler.communicate()
			
			if process_stderr.strip() != "":
				logit( "The Terraform provisioning has failed!", "error" )
				logit( process_stderr, "error" )
				logit( process_stdout, "error" )
				
				# Alert us of the provisioning error so we can get ahead of
				# it with AWS support.
				TerraformSpawner.send_terraform_provisioning_error(
					aws_account_data[ "account_id" ],
					str( process_stderr )
				)
				
				raise Exception( "Terraform provisioning failed, AWS account marked as \"CORRUPT\"" )
			
			logit( "Running 'terraform output' to pull the account details..." )
			
			# Print Terraform output as JSON so we can read it.
			process_handler = subprocess.Popen(
				[
					base_dir + "terraform",
					"output",
					"-json"
				],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False,
				universal_newlines=True,
				cwd=base_dir,
			)
			process_stdout, process_stderr = process_handler.communicate()
			
			# Parse Terraform JSON output
			terraform_provisioned_account_details = json.loads(
				process_stdout
			)
			
			logit( "Pulled Terraform output successfully." )
			
			# Pull the terraform state and pull it so we can later
			# make terraform changes to user accounts.
			terraform_state = ""
			with open( base_dir + "terraform.tfstate", "r" ) as file_handler:
				terraform_state = file_handler.read()
			
			terraform_configuration_data[ "terraform_state" ] = terraform_state

			# By default, set the redis hostname to the free-tier server.
			# If the output of terraform has another redis hostname we use that instead
			terraform_configuration_data[ "redis_hostname" ] = os.environ.get( "free_tier_redis_server_hostname" )
			terraform_configuration_data[ "ssh_public_key" ] = ""
			terraform_configuration_data[ "ssh_private_key" ] = ""

			if "redis_elastic_ip" in terraform_provisioned_account_details:
				terraform_configuration_data[ "redis_hostname" ] = terraform_provisioned_account_details[ "redis_elastic_ip" ][ "value" ]

			if "refinery_redis_ssh_key_public_key_openssh" in terraform_configuration_data:
				terraform_configuration_data[ "ssh_public_key" ] = terraform_provisioned_account_details[ "refinery_redis_ssh_key_public_key_openssh" ][ "value" ]

			if "refinery_redis_ssh_key_private_key_pem" in terraform_configuration_data:
				terraform_configuration_data[ "ssh_private_key" ] = terraform_provisioned_account_details[ "refinery_redis_ssh_key_private_key_pem" ][ "value" ]

		finally:
			# Ensure we clear the temporary directory no matter what
			shutil.rmtree( base_dir )
			
		return terraform_configuration_data

	@staticmethod
	def _get_assume_role_credentials( aws_account_id, session_lifetime ):
		# Generate ARN for the sub-account AWS administrator role
		sub_account_admin_role_arn = "arn:aws:iam::" + str( aws_account_id ) + ":role/" + os.environ.get( "customer_aws_admin_assume_role" )
		
		# Session lifetime must be a minimum of 15 minutes
		# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html#STS.Client.assume_role
		min_session_lifetime_seconds = 900
		if session_lifetime < min_session_lifetime_seconds:
			session_lifetime = min_session_lifetime_seconds
		
		role_session_name = "Refinery-Managed-Account-Support-" + get_urand_password( 12 )
		
		response = STS_CLIENT.assume_role(
			RoleArn=sub_account_admin_role_arn,
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
		
	@staticmethod
	def send_terraform_provisioning_error( aws_account_id, error_output ):
		EmailSpawner._send_email(
			os.environ.get( "alerts_email" ),
			"[AWS Account Provisioning Error] The Refinery AWS Account #" + aws_account_id + " Encountered a Fatal Error During Terraform Provisioning",
			pystache.render(
				EMAIL_TEMPLATES[ "terraform_provisioning_error_alert" ],
				{
					"aws_account_id": aws_account_id,
					"error_output": error_output,
				}
			),
			False,
		)

terraform_spawner = TerraformSpawner()