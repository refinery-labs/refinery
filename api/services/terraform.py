import json
import shutil


from copy import copy
from models import AWSAccount, TerraformStateVersion
from json import loads
from shutil import rmtree
from subprocess import Popen, PIPE
from tasks.email import send_terraform_provisioning_error
from tasks.role import get_assume_role_credentials
from time import time
from uuid import uuid4
from utils.general import logit
from pinject import copy_args_to_public_fields
from traceback import print_exc


class TerraformService(object):
    app_config = None
    sts_client = None
    preterraform_manager = None
    aws_client_factory = None  # type: AwsClientFactory
    db_session_maker = None
    task_spawner = None

    # noinspection PyUnresolvedReferences
    @copy_args_to_public_fields
    def __init__(
        self,
        app_config,
        sts_client,
        preterraform_manager,
        aws_client_factory,
        db_session_maker,
        task_spawner
    ):
        pass

    def write_terraform_base_files(self, aws_account_dict):
        # Create a temporary working directory for the work.
        # Even if there's some exception thrown during the process
        # we will still delete the underlying state.
        temporary_dir = "/tmp/" + str(uuid4()) + "/"

        try:
            # Recursively copy files to the directory
            shutil.copytree(
                "/work/install/",
                temporary_dir
            )

            return self._write_terraform_base_files(aws_account_dict, temporary_dir)
        except Exception as e:
            logit("An exception occurred while writing terraform base files for AWS account ID " +
                aws_account_dict["account_id"])
            logit(e)

            # Delete the temporary directory reguardless.
            rmtree(temporary_dir)

            raise

    # TODO rename this
    def _write_terraform_base_files(self, aws_account_data, base_dir):
        logit("Setting up the base Terraform files (AWS Acc. ID '" +
            aws_account_data["account_id"] + "')...")

        # Get some temporary assume role credentials for the account
        assumed_role_credentials = get_assume_role_credentials(
            self.app_config,
            self.sts_client,
            str(aws_account_data["account_id"]),
            3600  # One hour - TODO CHANGEME
        )

        sub_account_admin_role_arn = "arn:aws:iam::" + \
            str(aws_account_data["account_id"]) + ":role/" + \
            self.app_config.get("customer_aws_admin_assume_role")

        # Write out the terraform configuration data
        terraform_configuration_data = {
            "session_token": assumed_role_credentials["session_token"],
            "role_session_name": assumed_role_credentials["role_session_name"],
            "assume_role_arn": sub_account_admin_role_arn,
            "access_key": assumed_role_credentials["access_key_id"],
            "secret_key": assumed_role_credentials["secret_access_key"],
            "region": self.app_config.get("region_name"),
            "s3_bucket_suffix": aws_account_data["s3_bucket_suffix"],
            "redis_secrets": {
                "password": aws_account_data["redis_password"],
                "secret_prefix": aws_account_data["redis_secret_prefix"],
            }
        }

        logit("Writing Terraform input variables to file...")

        # Write configuration data to a file for Terraform to use.
        with open(base_dir + "customer_config.json", "w") as file_handler:
            file_handler.write(
                json.dumps(
                    terraform_configuration_data
                )
            )

        # Write the latest terraform state to terraform.tfstate
        # If we have any state at all.
        if aws_account_data["terraform_state"] != "":
            # First we write the current version to the database as a version to keep track

            terraform_state_file_path = base_dir + "terraform.tfstate"

            logit("A previous terraform state file exists! Writing it to '" +
                terraform_state_file_path + "'...")

            with open(terraform_state_file_path, "w") as file_handler:
                file_handler.write(
                    aws_account_data["terraform_state"]
                )

        logit("The base terraform files have been created successfully at " + base_dir)

        terraform_configuration_data["base_dir"] = base_dir

        return terraform_configuration_data

    def terraform_configure_aws_account(self, aws_account_data):
        logit("Ensuring existence of ECS service-linked role before continuing with AWS account configuration...")
        self.preterraform_manager._ensure_ecs_service_linked_role_exists(
            self.aws_client_factory,
            aws_account_data
        )

        terraform_configuration_data = self.write_terraform_base_files(aws_account_data)
        base_dir = terraform_configuration_data["base_dir"]

        try:
            logit("Setting up AWS account with terraform (AWS Acc. ID '" +
                aws_account_data["account_id"] + "')...")

            # Terraform apply
            process_handler = Popen(
                [
                    base_dir + "terraform",
                    "apply",
                    "-auto-approve",
                    "-var-file",
                    base_dir + "customer_config.json",
                ],
                stdout=PIPE,
                stderr=PIPE,
                shell=False,
                universal_newlines=True,
                cwd=base_dir,
            )
            process_stdout, process_stderr = process_handler.communicate()

            if process_stderr.strip() != "":
                logit("The Terraform provisioning has failed!", "error")
                logit(process_stderr, "error")
                logit(process_stdout, "error")

                # Alert us of the provisioning error so we can get ahead of
                # it with AWS support.
                send_terraform_provisioning_error(
                    self.app_config,
                    aws_account_data["account_id"],
                    str(process_stderr)
                )

                raise Exception(
                    "Terraform provisioning failed, AWS account marked as \"CORRUPT\"")

            logit("Running 'terraform output' to pull the account details...")

            # Print Terraform output as JSON so we can read it.
            process_handler = Popen(
                [
                    base_dir + "terraform",
                    "output",
                    "-json"
                ],
                stdout=PIPE,
                stderr=PIPE,
                shell=False,
                universal_newlines=True,
                cwd=base_dir,
            )
            process_stdout, process_stderr = process_handler.communicate()

            # Parse Terraform JSON output
            terraform_provisioned_account_details = loads(process_stdout)

            logit("Pulled Terraform output successfully.")

            # Pull the terraform state and pull it so we can later
            # make terraform changes to user accounts.
            terraform_state = ""
            with open(base_dir + "terraform.tfstate", "r") as file_handler:
                terraform_state = file_handler.read()

            terraform_configuration_data["terraform_state"] = terraform_state
            terraform_configuration_data["redis_hostname"] = terraform_provisioned_account_details["redis_elastic_ip"]["value"]
            terraform_configuration_data["ssh_public_key"] = terraform_provisioned_account_details[
                "refinery_redis_ssh_key_public_key_openssh"]["value"]
            terraform_configuration_data["ssh_private_key"] = terraform_provisioned_account_details[
                "refinery_redis_ssh_key_private_key_pem"]["value"]
        finally:
            # Ensure we clear the temporary directory no matter what
            rmtree(base_dir)

        return terraform_configuration_data

    def terraform_apply(self, aws_account_data, refresh_terraform_state):
        """
        This applies the latest terraform config to an account.

        THIS IS DANGEROUS, MAKE SURE YOU DID A FLEET TERRAFORM PLAN
        FIRST. NO EXCUSES, THIS IS ONE OF THE FEW WAYS TO BREAK PROD
        FOR OUR CUSTOMERS.

        -mandatory

        :param: refresh_terraform_state This value tells Terraform if it should refresh the state before running plan
        """

        logit("Ensuring existence of ECS service-linked role before continuing with terraform apply...")
        self.preterraform_manager._ensure_ecs_service_linked_role_exists(
            self.aws_client_factory,
            aws_account_data
        )

        # The return data
        return_data = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "original_tfstate": str(
                copy(
                    aws_account_data["terraform_state"]
                )
            ),
            "new_tfstate": "",
        }

        terraform_configuration_data = self.write_terraform_base_files(aws_account_data)
        temporary_directory = terraform_configuration_data["base_dir"]

        try:
            logit("Performing 'terraform apply' to AWS Account " +
                aws_account_data["account_id"] + "...")

            refresh_state_parameter = "true" if refresh_terraform_state else "false"

            # Terraform plan
            process_handler = Popen(
                [
                    temporary_directory + "terraform",
                    "apply",
                    "-refresh=" + refresh_state_parameter,
                    "-auto-approve",
                    "-var-file",
                    temporary_directory + "customer_config.json",
                ],
                stdout=PIPE,
                stderr=PIPE,
                shell=False,
                universal_newlines=True,
                cwd=temporary_directory,
            )
            process_stdout, process_stderr = process_handler.communicate()
            return_data["stdout"] = process_stdout
            return_data["stderr"] = process_stderr

            # Pull the latest terraform state and return it
            # We need to do this regardless of if an error occurred.
            with open(temporary_directory + "terraform.tfstate", "r") as file_handler:
                return_data["new_tfstate"] = file_handler.read()

            if process_stderr.strip() != "":
                logit("The 'terraform apply' has failed!", "error")
                logit(process_stderr, "error")
                logit(process_stdout, "error")

                # Alert us of the provisioning error so we can response to it
                send_terraform_provisioning_error(
                    self.app_config,
                    aws_account_data["account_id"],
                    str(process_stderr)
                )

                return_data["success"] = False
        finally:
            # Ensure we clear the temporary directory no matter what
            rmtree(temporary_directory)

        logit("'terraform apply' completed, returning results...")

        return return_data

    def terraform_plan(self, aws_account_data, refresh_terraform_state):
        """
        This does a terraform plan to an account and sends an email
        with the results. This allows us to see the impact of a new
        terraform change before we roll it out across our customer's
        AWS accounts.
        :param: refresh_terraform_state This value tells Terraform if it should refresh the state before running plan
        """

        terraform_configuration_data = self.write_terraform_base_files(aws_account_data)
        temporary_directory = terraform_configuration_data["base_dir"]

        try:
            logit("Performing 'terraform plan' to AWS account " +
                aws_account_data["account_id"] + "...")

            refresh_state_parameter = "true" if refresh_terraform_state else "false"

            # Terraform plan
            process_handler = Popen(
                [
                    temporary_directory + "terraform",
                    "plan",
                    "-refresh=" + refresh_state_parameter,
                    "-var-file",
                    temporary_directory + "customer_config.json",
                ],
                stdout=PIPE,
                stderr=PIPE,
                shell=False,
                universal_newlines=True,
                cwd=temporary_directory,
            )
            process_stdout, process_stderr = process_handler.communicate()

            if process_stderr.strip() != "":
                logit("The 'terraform plan' has failed!", "error")
                logit(process_stderr, "error")
                logit(process_stdout, "error")

                raise Exception("Terraform plan failed.")
        finally:
            # Ensure we clear the temporary directory no matter what
            rmtree(temporary_directory)

        logit("Terraform plan completed successfully, returning output.")

        return process_stdout

    def get_account_create_info(self):
        dbsession = self.db_session_maker()

        reserved_aws_pool_target_amount = int(self.app_config.get("reserved_aws_pool_target_amount"))

        # Get the number of AWS accounts which are ready to be
        # assigned to new users that are signing up ("AVAILABLE").
        available_accounts_count = dbsession.query(AWSAccount).filter_by(
            aws_account_status="AVAILABLE"
        ).count()

        # Get the number of AWS accounts which have been created
        # but are not yet provision via Terraform ("CREATED").
        created_accounts_count = dbsession.query(AWSAccount).filter_by(
            aws_account_status="CREATED"
        ).count()

        # Get the number of AWS accounts that need to be provision
        # via Terraform on this iteration
        # At a MINIMUM we have to wait 60 seconds from the time of account creation
        # to actually perform the Terraform step.
        # We'll do 20 because it usually takes 15 to get the "Account Verified" email.
        minimum_account_age_seconds = (60 * 5)
        current_timestamp = int(time())
        non_setup_aws_accounts = dbsession.query(AWSAccount).filter(
            AWSAccount.aws_account_status == "CREATED",
            AWSAccount.timestamp <= (current_timestamp - minimum_account_age_seconds)
        ).all()
        non_setup_aws_accounts_count = len(non_setup_aws_accounts)

        # Pull the list of AWS account IDs to work on.
        aws_account_ids = []
        for non_setup_aws_account in non_setup_aws_accounts:
            aws_account_ids.append(
                non_setup_aws_account.account_id
            )

        dbsession.close()

        # Calculate the number of accounts that have been created but not provisioned
        # That way we know how many, if any, that we need to create.
        accounts_to_create = (reserved_aws_pool_target_amount - available_accounts_count - created_accounts_count)
        if accounts_to_create < 0:
            accounts_to_create = 0

        self.logger("--- AWS Account Stats ---")
        self.logger("Ready for customer use: " + str(available_accounts_count))
        self.logger("Ready for terraform provisioning: " + str(non_setup_aws_accounts_count))
        self.logger("Not ready for initial terraform provisioning: " + str((created_accounts_count - non_setup_aws_accounts_count)))
        self.logger("Target pool amount: " + str(reserved_aws_pool_target_amount))
        self.logger("Number of accounts to be created: " + str(accounts_to_create))

        return aws_account_ids, accounts_to_create

    def terraform_apply_aged_account(self, aws_account_id):
        dbsession = self.db_session_maker()
        current_aws_account = dbsession.query(AWSAccount).filter(
            AWSAccount.account_id == aws_account_id,
        ).first()
        current_aws_account_dict = current_aws_account.to_dict()
        dbsession.close()

        self.logger("Kicking off terraform set-up for AWS account '" + current_aws_account_dict["account_id"] + "'...")
        try:
            account_provisioning_details = yield self.task_spawner.terraform_configure_aws_account(
                current_aws_account_dict
            )

            self.logger("Adding AWS account to the database the pool of \"AVAILABLE\" accounts...")

            dbsession = self.db_session_maker()
            current_aws_account = dbsession.query(AWSAccount).filter(
                AWSAccount.account_id == aws_account_id,
            ).first()

            # Update the AWS account with this new information
            current_aws_account.redis_hostname = account_provisioning_details["redis_hostname"]
            current_aws_account.terraform_state = account_provisioning_details["terraform_state"]
            current_aws_account.ssh_public_key = account_provisioning_details["ssh_public_key"]
            current_aws_account.ssh_private_key = account_provisioning_details["ssh_private_key"]
            current_aws_account.aws_account_status = "AVAILABLE"

            # Create a new terraform state version
            terraform_state_version = TerraformStateVersion()
            terraform_state_version.terraform_state = account_provisioning_details["terraform_state"]
            current_aws_account.terraform_state_versions.append(
                terraform_state_version
            )
        except Exception as e:
            self.logger("An error occurred while provision AWS account '" + current_aws_account.account_id + "' with terraform!", "error")
            self.logger(e)
            print_exc()
            self.logger("Marking the account as 'CORRUPT'...")

            # Mark the account as corrupt since the provisioning failed.
            current_aws_account.aws_account_status = "CORRUPT"

        self.logger("Commiting new account state of '" + current_aws_account.aws_account_status + "' to database...")
        dbsession.add(current_aws_account)
        dbsession.commit()

        self.logger("Freezing the account until it's used by someone...")

        self.task_spawner.freeze_aws_account(current_aws_account.to_dict())

        self.logger("Account frozen successfully.")

    def create_sub_account_for_later_use(self):
        self.logger("Creating a new AWS sub-account for later terraform use...")
        # We have to yield because you can't mint more than one sub-account at a time
        # (AWS can litterally only process one request at a time).
        try:
            yield self.task_spawner.create_new_sub_aws_account(
                "MANAGED",
                False
            )
        except Exception as e:
            self.logger("An error occurred while creating an AWS sub-account: " + repr(e), "error")

    def maintain_aws_account_reserves(self):
        """
        This job checks the number of AWS accounts in the reserve pool and will
        automatically create accounts for the pool if there are less than the
        target amount. This job is run regularly (every minute) to ensure that
        we always have enough AWS accounts ready to use.
        """

        aws_account_ids, accounts_to_create = self.get_account_create_info()

        # Kick off the terraform apply jobs for the accounts which are "aged" for it.
        for aws_account_id in aws_account_ids:
            self.terraform_apply_aged_account(aws_account_id)

        # Create sub-accounts and let them age before applying terraform
        for i in range(0, accounts_to_create):
            self.create_sub_account_for_later_use()
