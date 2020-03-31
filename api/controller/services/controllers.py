import time

import pinject
from ansi2html import Ansi2HTMLConverter
from sqlalchemy import or_ as sql_or
from tornado import gen

from assistants.deployments.teardown import teardown_infrastructure
from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from controller import BaseHandler
from controller.services.actions import clear_sub_account_packages, get_last_month_start_and_end_date_strings
from models import AWSAccount, User, TerraformStateVersion
from assistants.deployments.dangling_resources import get_user_dangling_resources
from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME


class AdministrativeAssumeAccount( BaseHandler ):
	def get( self, user_id=None ):
		"""
		For helping customers with their accounts.
		"""
		if not user_id:
			self.write({
				"success": False,
				"msg": "You must specify a user_id via the URL (/UUID/)."
			})

		# Authenticate the user via secure cookie
		self.authenticate_user_id(
			user_id
		)

		self.redirect(
			"/"
		)


class UpdateIAMConsoleUserIAM( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		This blows away all the IAM policies for all customer AWS accounts
		and updates it with the latest policy.
		"""
		self.write({
			"success": True,
			"msg": "Console accounts are being updated!"
		})
		self.finish()

		dbsession = self.db_session_maker()
		aws_accounts = dbsession.query( AWSAccount ).filter(
			sql_or(
				AWSAccount.aws_account_status == "IN_USE",
				AWSAccount.aws_account_status == "AVAILABLE",
				)
		).all()

		aws_account_dicts = []
		for aws_account in aws_accounts:
			aws_account_dicts.append(
				aws_account.to_dict()
			)
		dbsession.close()

		for aws_account_dict in aws_account_dicts:
			self.logger( "Updating console account for AWS account ID " + aws_account_dict[ "account_id" ] + "...")
			yield self.task_spawner.recreate_aws_console_account(
				aws_account_dict,
				False
			)

		self.logger( "AWS console accounts updated successfully!" )

class OnboardThirdPartyAWSAccountPlan( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		Imports a third-party AWS account into the database and sends out
		a terraform plan email with what will happen when it's fully set up.
		"""

		# Get AWS account ID
		account_id = self.get_argument(
			"account_id",
			default=None,
			strip=True
		)

		if not account_id:
			self.write({
				"success": False,
				"msg": "Please provide an 'account_id' to onboard this AWS account!"
			})
			raise gen.Return()

		final_email_html = """
		<h1>Terraform Plan Results for Onboarding Third-Party Customer AWS Account</h1>
		Please note that this is <b>not</b> applying these changes.
		It is purely to understand what would happen if we did.
		"""

		# First we set up the AWS Account in our database so we have a record
		# of it going forward. This also creates the AWS console user.
		self.logger( "Adding third-party AWS account to the database..." )
		yield self.task_spawner.create_new_sub_aws_account(
			"THIRDPARTY",
			account_id
		)

		dbsession = self.db_session_maker()
		third_party_aws_account = dbsession.query( AWSAccount ).filter_by(
			account_id=account_id,
			account_type="THIRDPARTY"
		).first()
		third_party_aws_account_dict = third_party_aws_account.to_dict()
		dbsession.close()

		self.logger( "Performing a terraform plan against the third-party account..." )
		terraform_plan_output = yield self.task_spawner.terraform_plan(
			third_party_aws_account_dict
		)

		# Convert terraform plan terminal output to HTML
		ansiconverter = Ansi2HTMLConverter()
		terraform_output_html = ansiconverter.convert(
			terraform_plan_output
		)

		final_email_html += "<hr /><h1>AWS Account " + third_party_aws_account_dict[ "account_id" ] + "</h1>"
		final_email_html += terraform_output_html

		final_email_html += "<hr /><b>That is all.</b>"

		self.logger( "Sending email with results from terraform plan..." )
		yield self.task_spawner.send_email(
			self.app_config.get( "alerts_email" ),

			# Make subject unique so Gmail doesn't group
			"Terraform Plan Results for Onboarding Third-Party AWS Account " + str( int( time.time() ) ),

			# No text version of email
			False,

			final_email_html
		)

		self.write({
			"success": True,
			"msg": "Successfully added AWS account " + account_id + " to database and sent plan email!"
		})


class OnboardThirdPartyAWSAccountApply( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		Finalizes the third-party AWS account onboarding import process.

		This should only be done after the Terraform plan has been reviewed
		and it looks appropriate to be applied.
		"""

		# Get AWS account ID
		account_id = self.get_argument(
			"account_id",
			default=None,
			strip=True
		)

		# Get Refinery user ID
		user_id = self.get_argument(
			"user_id",
			default=None,
			strip=True
		)

		if not account_id:
			self.write({
				"success": False,
				"msg": "Please provide an 'account_id' to onboard this AWS account!"
			})
			raise gen.Return()

		if not user_id:
			self.write({
				"success": False,
				"msg": "Please provide an 'user_id' to onboard this AWS account!"
			})
			raise gen.Return()

		dbsession = self.db_session_maker()
		third_party_aws_account = dbsession.query( AWSAccount ).filter_by(
			account_id=account_id,
			account_type="THIRDPARTY"
		).first()
		third_party_aws_account_dict = third_party_aws_account.to_dict()
		dbsession.close()

		self.logger( "Creating the '" + THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME + "' role for Lambda executions..." )
		yield self.task_spawner.create_third_party_aws_lambda_execute_role(
			third_party_aws_account_dict
		)

		try:
			self.logger( "Creating Refinery base infrastructure on third-party AWS account..." )
			account_provisioning_details = yield self.task_spawner.terraform_configure_aws_account(
				third_party_aws_account_dict
			)

			dbsession = self.db_session_maker()

			# Get the AWS account specified
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == account_id,
				).first()

			# Pull the user from the database
			refinery_user = dbsession.query( User ).filter_by(
				id=user_id
			).first()

			# Grab the previous AWS account specified with the Refinery account
			previous_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.organization_id == refinery_user.organization_id
			).first()

			previous_aws_account_dict = previous_aws_account.to_dict()
			previous_aws_account_id = previous_aws_account.id

			self.logger( "Previously-assigned AWS Account has UUID of " + previous_aws_account_id )

			# Set the previously-assigned AWS account to be
			previous_aws_account.aws_account_status = "NEEDS_CLOSING"
			previous_aws_account.organization_id = None

			# Update the AWS account with this new information
			current_aws_account.redis_hostname = account_provisioning_details[ "redis_hostname" ]
			current_aws_account.terraform_state = account_provisioning_details[ "terraform_state" ]
			current_aws_account.ssh_public_key = account_provisioning_details[ "ssh_public_key" ]
			current_aws_account.ssh_private_key = account_provisioning_details[ "ssh_private_key" ]
			current_aws_account.aws_account_status = "IN_USE"
			current_aws_account.organization_id = refinery_user.organization_id

			# Create a new terraform state version
			terraform_state_version = TerraformStateVersion()
			terraform_state_version.terraform_state = account_provisioning_details[ "terraform_state" ]
			current_aws_account.terraform_state_versions.append(
				terraform_state_version
			)
		except Exception as e:
			self.logger( "An error occurred while provision AWS account '" + current_aws_account.account_id + "' with terraform!", "error" )
			self.logger( e )
			self.logger( "Marking the account as 'CORRUPT'..." )

			# Mark the account as corrupt since the provisioning failed.
			current_aws_account.aws_account_status = "CORRUPT"
			dbsession.add( current_aws_account )
			dbsession.commit()
			dbsession.close()

			self.write({
				"success": False,
				"exception": str( e ),
				"msg": "An error occurred while provisioning AWS account."
			})

			raise gen.Return()

		self.logger( "AWS account terraform apply has completed." )
		dbsession.add( previous_aws_account )
		dbsession.add( current_aws_account )
		dbsession.commit()
		dbsession.close()

		# Close the previous Refinery-managed AWS account
		self.logger( "Closing previously-assigned Refinery AWS account..." )
		self.logger( "Freezing the account so it costs us less while we do the process of closing it..." )
		yield self.task_spawner.freeze_aws_account(
			previous_aws_account_dict
		)

		self.write({
			"success": True,
			"msg": "Successfully added third-party AWS account " + account_id + " to user ID " + user_id + "."
		})

class ClearAllS3BuildPackages( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		Clears out the S3 build packages of all the Refinery users.

		This just forces everyone to do a rebuild the next time they run code with packages.
		"""
		self.write({
			"success": True,
			"msg": "Clear build package job kicked off successfully!"
		})
		self.finish()

		dbsession = self.db_session_maker()
		aws_accounts = dbsession.query( AWSAccount ).filter(
			sql_or(
				AWSAccount.aws_account_status == "IN_USE",
				AWSAccount.aws_account_status == "AVAILABLE",
				)
		).all()

		aws_account_dicts = []
		for aws_account in aws_accounts:
			aws_account_dicts.append(
				aws_account.to_dict()
			)
		dbsession.close()

		for aws_account_dict in aws_account_dicts:
			self.logger( "Clearing build packages for account ID " + aws_account_dict[ "account_id" ] + "..." )
			yield clear_sub_account_packages(
				self.task_spawner,
				aws_account_dict
			)

		self.logger( "S3 package clearing complete." )


class MaintainAWSAccountReserves( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		This job checks the number of AWS accounts in the reserve pool and will
		automatically create accounts for the pool if there are less than the
		target amount. This job is run regularly (every minute) to ensure that
		we always have enough AWS accounts ready to use.
		"""
		self.write({
			"success": True,
			"msg": "AWS account maintenance job has been kicked off!"
		})
		self.finish()

		dbsession = self.db_session_maker()

		reserved_aws_pool_target_amount = int( self.app_config.get( "reserved_aws_pool_target_amount" ) )

		# Get the number of AWS accounts which are ready to be
		# assigned to new users that are signing up ("AVAILABLE").
		available_accounts_count = dbsession.query( AWSAccount ).filter_by(
			aws_account_status="AVAILABLE"
		).count()

		# Get the number of AWS accounts which have been created
		# but are not yet provision via Terraform ("CREATED").
		created_accounts_count = dbsession.query( AWSAccount ).filter_by(
			aws_account_status="CREATED"
		).count()

		# Get the number of AWS accounts that need to be provision
		# via Terraform on this iteration
		# At a MINIMUM we have to wait 60 seconds from the time of account creation
		# to actually perform the Terraform step.
		# We'll do 20 because it usually takes 15 to get the "Account Verified" email.
		minimum_account_age_seconds = ( 60 * 5 )
		current_timestamp = int( time.time() )
		non_setup_aws_accounts = dbsession.query( AWSAccount ).filter(
			AWSAccount.aws_account_status == "CREATED",
			AWSAccount.timestamp <= ( current_timestamp - minimum_account_age_seconds )
		).all()
		non_setup_aws_accounts_count = len( non_setup_aws_accounts )

		# Pull the list of AWS account IDs to work on.
		aws_account_ids = []
		for non_setup_aws_account in non_setup_aws_accounts:
			aws_account_ids.append(
				non_setup_aws_account.account_id
			)

		dbsession.close()

		# Calculate the number of accounts that have been created but not provisioned
		# That way we know how many, if any, that we need to create.
		accounts_to_create = ( reserved_aws_pool_target_amount - available_accounts_count - created_accounts_count )
		if accounts_to_create < 0:
			accounts_to_create = 0

		self.logger( "--- AWS Account Stats ---" )
		self.logger( "Ready for customer use: " + str( available_accounts_count ) )
		self.logger( "Ready for terraform provisioning: " + str( non_setup_aws_accounts_count ) )
		self.logger( "Not ready for initial terraform provisioning: " + str( ( created_accounts_count - non_setup_aws_accounts_count ) ) )
		self.logger( "Target pool amount: " + str( reserved_aws_pool_target_amount ) )
		self.logger( "Number of accounts to be created: " + str( accounts_to_create ) )

		# Kick off the terraform apply jobs for the accounts which are "aged" for it.
		for aws_account_id in aws_account_ids:
			dbsession = self.db_session_maker()
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == aws_account_id,
				).first()
			current_aws_account_dict = current_aws_account.to_dict()
			dbsession.close()

			self.logger( "Kicking off terraform set-up for AWS account '" + current_aws_account_dict[ "account_id" ] + "'..." )
			try:
				account_provisioning_details = yield self.task_spawner.terraform_configure_aws_account(
					current_aws_account_dict
				)

				self.logger( "Adding AWS account to the database the pool of \"AVAILABLE\" accounts..." )

				dbsession = self.db_session_maker()
				current_aws_account = dbsession.query( AWSAccount ).filter(
					AWSAccount.account_id == aws_account_id,
					).first()

				# Update the AWS account with this new information
				current_aws_account.redis_hostname = account_provisioning_details[ "redis_hostname" ]
				current_aws_account.terraform_state = account_provisioning_details[ "terraform_state" ]
				current_aws_account.ssh_public_key = account_provisioning_details[ "ssh_public_key" ]
				current_aws_account.ssh_private_key = account_provisioning_details[ "ssh_private_key" ]
				current_aws_account.aws_account_status = "AVAILABLE"

				# Create a new terraform state version
				terraform_state_version = TerraformStateVersion()
				terraform_state_version.terraform_state = account_provisioning_details[ "terraform_state" ]
				current_aws_account.terraform_state_versions.append(
					terraform_state_version
				)
			except Exception as e:
				self.logger( "An error occurred while provision AWS account '" + current_aws_account.account_id + "' with terraform!", "error" )
				self.logger( e )
				self.logger( "Marking the account as 'CORRUPT'..." )

				# Mark the account as corrupt since the provisioning failed.
				current_aws_account.aws_account_status = "CORRUPT"

			self.logger( "Commiting new account state of '" + current_aws_account.aws_account_status + "' to database..." )
			dbsession.add(current_aws_account)
			dbsession.commit()

			self.logger( "Freezing the account until it's used by someone..." )

			TaskSpawner._freeze_aws_account(
				self.db_session_maker,
				current_aws_account.to_dict()
			)

			self.logger( "Account frozen successfully." )

		# Create sub-accounts and let them age before applying terraform
		for i in range( 0, accounts_to_create ):
			self.logger( "Creating a new AWS sub-account for later terraform use..." )
			# We have to yield because you can't mint more than one sub-account at a time
			# (AWS can litterally only process one request at a time).
			try:
				yield self.task_spawner.create_new_sub_aws_account(
					"MANAGED",
					False
				)
			except:
				self.logger( "An error occurred while creating an AWS sub-account.", "error" )
				pass

		dbsession.close()


class PerformTerraformUpdateOnFleet( BaseHandler ):
	@gen.coroutine
	def get( self ):
		self.write({
			"success": True,
			"msg": "Terraform apply job has been kicked off, I hope you planned first!"
		})
		self.finish()

		dbsession = self.db_session_maker()

		aws_accounts = dbsession.query( AWSAccount ).filter(
			sql_or(
				AWSAccount.aws_account_status == "IN_USE",
				AWSAccount.aws_account_status == "AVAILABLE",
				)
		).all()

		final_email_html = """
		<h1>Terraform Apply Results Across the Customer Fleet</h1>
		If the subject line doesn't read <b>APPLY SUCCEEDED</b> you have some work to do!
		"""

		issue_occurred_during_updates = False

		# Pull the list of AWS account IDs to work on.
		aws_account_ids = []
		for aws_account in aws_accounts:
			aws_account_ids.append(
				aws_account.account_id
			)

		dbsession.close()

		for aws_account_id in aws_account_ids:
			dbsession = self.db_session_maker()
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == aws_account_id,
				).first()
			current_aws_account_dict = current_aws_account.to_dict()
			dbsession.close()

			self.logger( "Running 'terraform apply' against AWS Account " + current_aws_account_dict[ "account_id" ] )
			terraform_apply_results = yield self.task_spawner.terraform_apply(
				current_aws_account_dict
			)

			# Write the old terraform version to the database
			self.logger( "Updating current tfstate for the AWS account..." )

			dbsession = self.db_session_maker()
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == aws_account_id,
				).first()

			previous_terraform_state = TerraformStateVersion()
			previous_terraform_state.aws_account_id = current_aws_account.id
			previous_terraform_state.terraform_state = terraform_apply_results[ "original_tfstate" ]
			current_aws_account.terraform_state_versions.append(
				previous_terraform_state
			)

			# Update the current terraform state as well.
			current_aws_account.terraform_state = terraform_apply_results[ "new_tfstate" ]

			dbsession.add( current_aws_account )
			dbsession.commit()
			dbsession.close()

			# Convert terraform plan terminal output to HTML
			ansiconverter = Ansi2HTMLConverter()

			if terraform_apply_results[ "success" ]:
				terraform_output_html = ansiconverter.convert(
					terraform_apply_results[ "stdout" ]
				)
			else:
				terraform_output_html = ansiconverter.convert(
					terraform_apply_results[ "stderr" ]
				)
				issue_occurred_during_updates = True

			final_email_html += "<hr /><h1>AWS Account " + current_aws_account_dict[ "account_id" ] + "</h1>"
			final_email_html += terraform_output_html

		final_email_html += "<hr /><b>That is all.</b>"

		self.logger( "Sending email with results from 'terraform apply'..." )

		final_email_subject = "Terraform Apply Results from Across the Fleet " + str( int( time.time() ) ) # Make subject unique so Gmail doesn't group
		if issue_occurred_during_updates:
			final_email_subject = "[ APPLY FAILED ] " + final_email_subject
		else:
			final_email_subject = "[ APPLY SUCCEEDED ] " + final_email_subject

		yield self.task_spawner.send_email(
			self.app_config.get( "alerts_email" ),
			final_email_subject,
			False, # No text version of email
			final_email_html
		)

		dbsession.close()

class PerformTerraformPlanOnFleet( BaseHandler ):
	@gen.coroutine
	def get( self ):
		self.write({
			"success": True,
			"msg": "Terraform plan job has been kicked off!"
		})
		self.finish()

		dbsession = self.db_session_maker()

		aws_accounts = dbsession.query( AWSAccount ).filter(
			sql_or(
				AWSAccount.aws_account_status == "IN_USE",
				AWSAccount.aws_account_status == "AVAILABLE",
				)
		).all()

		final_email_html = """
		<h1>Terraform Plan Results Across the Customer Fleet</h1>
		Please note that this is <b>not</b> applying these changes.
		It is purely to understand what would happen if we did.
		"""

		total_accounts = len( aws_accounts )
		counter = 1

		# Pull the list of AWS account IDs to work on.
		aws_account_ids = []
		for aws_account in aws_accounts:
			aws_account_ids.append(
				aws_account.account_id
			)

		dbsession.close()

		for aws_account_id in aws_account_ids:
			dbsession = self.db_session_maker()
			current_aws_account = dbsession.query( AWSAccount ).filter(
				AWSAccount.account_id == aws_account_id,
				).first()
			current_aws_account = current_aws_account.to_dict()
			dbsession.close()

			self.logger( "Performing a terraform plan for AWS account " + str( counter ) + "/" + str( total_accounts ) + "..." )
			terraform_plan_output = yield self.task_spawner.terraform_plan(
				current_aws_account
			)

			# Convert terraform plan terminal output to HTML
			ansiconverter = Ansi2HTMLConverter()
			terraform_output_html = ansiconverter.convert(
				terraform_plan_output
			)

			final_email_html += "<hr /><h1>AWS Account " + current_aws_account[ "account_id" ] + "</h1>"
			final_email_html += terraform_output_html
			counter = counter + 1

		final_email_html += "<hr /><b>That is all.</b>"

		self.logger( "Sending email with results from terraform plan..." )
		yield self.task_spawner.send_email(
			self.app_config.get( "alerts_email" ),
			"Terraform Plan Results from Across the Fleet " + str( int( time.time() ) ), # Make subject unique so Gmail doesn't group
			False, # No text version of email
			final_email_html
		)


class RunBillingWatchdogJob( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		This job checks the running account totals of each AWS account to see
		if their usage has gone over the safety limits. This is mainly for free
		trial users and for alerting users that they may incur a large bill.
		"""
		self.write({
			"success": True,
			"msg": "Watchdog job has been started!"
		})
		self.finish()
		self.logger( "[ STATUS ] Initiating billing watchdog job, scanning all accounts to check for billing anomalies..." )
		aws_account_running_cost_list = yield self.task_spawner.pull_current_month_running_account_totals()
		self.logger( "[ STATUS ] " + str( len( aws_account_running_cost_list ) ) + " account(s) pulled from billing, checking against rules..." )
		yield self.task_spawner.enforce_account_limits( aws_account_running_cost_list )


class RunMonthlyStripeBillingJob( BaseHandler ):
	@gen.coroutine
	def get( self ):
		"""
		Runs at the first of the month and creates auto-finalizing draft
		invoices for all Refinery customers. After it does this it emails
		the "billing_alert_email" email with a notice to review the drafts
		before they auto-finalize after one-hour.
		"""
		self.write({
			"success": True,
			"msg": "The billing job has been started!"
		})
		self.finish()
		self.logger( "[ STATUS ] Running monthly Stripe billing job to invoice all Refinery customers." )
		date_info = get_last_month_start_and_end_date_strings()

		self.logger( "[ STATUS ] Generating invoices for " + date_info[ "month_start_date" ] + " -> " + date_info[ "next_month_first_day" ]  )

		yield self.task_spawner.generate_managed_accounts_invoices(
			date_info[ "month_start_date"],
			date_info[ "next_month_first_day" ],
		)
		self.logger( "[ STATUS ] Stripe billing job has completed!" )


class CleanupDanglingResourcesDependencies:
	@pinject.copy_args_to_public_fields
	def __init__(
			self,
			lambda_manager,
			api_gateway_manager,
			schedule_trigger_manager,
			sns_manager,
			sqs_manager,
			aws_resource_enumerator
	):
		pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class CleanupDanglingResources( BaseHandler ):
	dependencies = CleanupDanglingResourcesDependencies
	lambda_manager = None
	api_gateway_manager = None
	schedule_trigger_manager = None
	sns_manager = None
	sqs_manager = None
	aws_resource_enumerator = None

	@gen.coroutine
	def get( self, user_id=None ):
		delete_resources = self.get_argument( "confirm", False )

		# Get user's organization
		user = self.dbsession.query( User ).filter_by(
			id=user_id
		).first()

		if not user:
			self.write({
				"success": False,
				"msg": "No user was found with that UUID."
			})
			raise gen.Return()

		aws_account = self.dbsession.query( AWSAccount ).filter_by(
			organization_id=user.organization_id,
			aws_account_status="IN_USE"
		).first()

		if not aws_account:
			self.write({
				"success": False,
				"msg": "No AWS account found for user."
			})
			raise gen.Return()

		# Get credentials to perform scan
		credentials = aws_account.to_dict()

		# Get user dangling records
		dangling_resources = yield get_user_dangling_resources(
			self.aws_resource_enumerator,
			self.db_session_maker,
			user_id,
			credentials
		)

		number_of_resources = len( dangling_resources )

		self.logger( str( len( dangling_resources ) ) + " resource(s) enumerated in account." )

		# If the "confirm" parameter is passed we can proceed to delete it all.
		if delete_resources:
			self.logger( "Deleting all dangling resources..." )

			# Tear down all dangling nodes
			teardown_results = yield teardown_infrastructure(
				self.api_gateway_manager,
				self.lambda_manager,
				self.schedule_trigger_manager,
				self.sns_manager,
				self.sqs_manager,
				credentials,
				dangling_resources
			)

			self.logger( teardown_results )

			self.logger( "Deleted all dangling resources successfully!" )

		self.write({
			"success": True,
			"total_resources": len( dangling_resources ),
			"result": dangling_resources
		})


class ClearStripeInvoiceDraftsDependencies:
	@pinject.copy_args_to_public_fields
	def __init__( self, billing_spawner ):
		pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class ClearStripeInvoiceDrafts( BaseHandler ):
	dependencies = ClearStripeInvoiceDraftsDependencies
	billing_spawner = None

	@gen.coroutine
	def get( self ):
		self.logger( "Clearing all draft Stripe invoices..." )
		yield self.billing_spawner.clear_draft_invoices()

		self.write({
			"success": True,
			"msg": "Invoice drafts have been cleared!"
		})