import json
import shutil


from copy import copy
from models import AWSAccount, TerraformStateVersion
from json import loads
from os.path import join
from shutil import rmtree
from tasks.email import send_terraform_provisioning_error
from tasks.role import get_assume_role_credentials
from time import time
from uuid import uuid4
from utils.general import logit
from utils.ipc import popen_communicate
from pinject import copy_args_to_public_fields
from traceback import print_exc


TERRAFORM_TFSTATE = "terraform.tfstate"
CUSTOMER_CONFIG_JSON = "customer_config.json"


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

            return self._write_terraform_base_files(
                aws_account_dict,
                temporary_dir
            )
        except Exception as e:
            msg = (
                "Exception occurred while writing terraform base files "
                "for AWS account ID: {}"
            )
            logit(msg.format(aws_account_dict['account_id']))
            logit(e)

            # Delete the temporary directory reguardless.
            rmtree(temporary_dir)

            raise

    # TODO rename this
    def _write_terraform_base_files(self, aws_account_data, base_dir):
        msg = 'Setting up base Terraform files (AWS Acc ID: "{}")...'
        logit(msg.format(aws_account_data['account_id']))

        # Get some temporary assume role credentials for the account
        assumed_role_credentials = get_assume_role_credentials(
            self.app_config,
            self.sts_client,
            str(aws_account_data["account_id"]),
            3600  # One hour - TODO CHANGEME
        )

        sub_account_admin_role_arn = self.get_sub_account_admin_role_arn(aws_account_data)

        # Write out the terraform configuration data
        terraform_configuration_data = self.get_terraform_config(
            aws_account_data,
            assumed_role_credentials,
            sub_account_admin_role_arn
        )

        logit("Writing Terraform input variables to file...")
        self.write_customer_config(terraform_configuration_data, base_dir)

        self.write_terraform_state(aws_account_data, base_dir)
        logit(f"Base terraform files have been created successfully at {base_dir}")

        terraform_configuration_data["base_dir"] = base_dir

        return terraform_configuration_data

    def get_sub_account_admin_role_arn(self, aws_account_data):
        account_id = str(aws_account_data['account_id'])
        # TODO what if this is None?
        assume_role = self.app_config.get("customer_aws_admin_assume_role")

        return f"arn:aws_iam::{account_id}:role/{assume_role}"

    def write_customer_config(self, config, base_dir):
        # Write configuration data to a file for Terraform to use.
        with open(join(base_dir, CUSTOMER_CONFIG_JSON), "w") as f:
            f.write(json.dumps(config))

    def write_terraform_state(self, aws_account_data, base_dir):
        """
        Write the latest terraform state to terraform.tfstate if there is any.
        """
        if not aws_account_data["terraform_state"]:
            # Write the current version to the database

            path = join(base_dir, TERRAFORM_TFSTATE)
            logit(f'Previous terraform state file exists! Writing to "{path}"')

            with open(path, "w") as f:
                f.write(aws_account_data["terraform_state"])

    def read_terraform_state(self, base_dir):
        path = join(base_dir, TERRAFORM_TFSTATE)

        with open(path, "r") as f:
            return f.read()

    def get_terraform_config(self, aws_account_data, credentials, role_arn):
        return {
            "session_token": credentials["session_token"],
            "role_session_name": credentials["role_session_name"],
            "assume_role_arn": role_arn,
            "access_key": credentials["access_key_id"],
            "secret_key": credentials["secret_access_key"],
            "region": self.app_config.get("region_name"),
            "s3_bucket_suffix": aws_account_data["s3_bucket_suffix"],
            "redis_secrets": {
                "password": aws_account_data["redis_password"],
                "secret_prefix": aws_account_data["redis_secret_prefix"],
            }
        }

    def terraform_configure_aws_account(self, aws_account_data):
        logit("Ensuring existence of ECS service-linked role before continuing with AWS account configuration...")
        self.preterraform_manager._ensure_ecs_service_linked_role_exists(
            self.aws_client_factory,
            aws_account_data
        )

        terraform_config = self.write_terraform_base_files(aws_account_data)
        base_dir = terraform_config["base_dir"]

        try:
            self.setup_aws_account_with_terraform(aws_account_data, terraform_config)

            logit("Running 'terraform output' to pull the account details...")

            terraform_output = self.terraform_output(terraform_config)
            terraform_state = self.read_terraform_state(base_dir)
            logit("Pulled Terraform output successfully.")

        finally:
            # Ensure we clear the temporary directory no matter what
            rmtree(base_dir)

        return self.get_terraform_aws_account_config(
            terraform_config,
            terraform_state,
            terraform_output
        )

    def get_terraform_aws_account_config(self, config, state, output):
        result = {}

        result.update(config)

        result["terraform_state"] = state
        result["redis_hostname"] = output["redis_elastic_ip"]["value"]
        result["ssh_public_key"] = output["refinery_redis_ssh_key_public_key_openssh"]["value"]
        result["ssh_private_key"] = output["refinery_redis_ssh_key_private_key_pem"]["value"]

        return result

    def setup_aws_account_with_terraform(self, aws_account_data, terraform_config):
        base_dir = terraform_config["base_dir"]

        # Terraform apply
        stdout, stderr = popen_communicate([
            base_dir + "terraform",
            "apply",
            "-auto-approve",
            "-var-file",
            join(base_dir, CUSTOMER_CONFIG_JSON)
        ], cwd=base_dir)

        self.handle_terraform_result(
            'Terraform provisioning failed, AWS account marked as "CORRUPT"',
            stderr,
            stdout,
            aws_account_data,
            throw=True,
            email=True
        )

    def terraform_output(self, terraform_config):
        base_dir = terraform_config["base_dir"]

        # Print Terraform output as readable JSON
        stdout, stderr = popen_communicate([
            base_dir + "terraform",
            "output",
            "-json"
        ], cwd=base_dir)

        # Parse Terraform JSON output
        return loads(stdout)

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
        result = {
            "success": True,
            "stdout": None,
            "stderr": None,
            "original_tfstate": str(
                copy(
                    aws_account_data["terraform_state"]
                )
            ),
            "new_tfstate": "",
        }

        terraform_configuration_data = self.write_terraform_base_files(aws_account_data)
        base_dir = terraform_configuration_data["base_dir"]

        try:
            msg = "Performing 'terraform apply' to AWS Account {}..."
            logit(msg.format(aws_account_data["account_id"]))

            refresh_state = str(bool(refresh_terraform_state)).lower()

            # Terraform plan
            process_stdout, process_stderr = popen_communicate([
                    join(base_dir, "terraform"),
                    "apply",
                    "-refresh=" + refresh_state,
                    "-auto-approve",
                    "-var-file",
                    join(base_dir, CUSTOMER_CONFIG_JSON)
                ], cwd=base_dir
            )
            result["stdout"] = process_stdout
            result["stderr"] = process_stderr

            # Pull the latest terraform state and return it
            # We need to do this regardless of if an error occurred.
            result['new_tfstate'] = self.read_terraform_state(base_dir)
            result['success'] = self.handle_terraform_result(
                "The 'terraform apply' has failed!",
                process_stderr,
                process_stdout,
                aws_account_data,
                email=True
            )
        finally:
            # Ensure we clear the temporary directory no matter what
            rmtree(base_dir)

        logit("'terraform apply' completed, returning results...")

        return result

    def handle_terraform_result(self, msg, stderr, stdout, aws_account_data, email=False, throw=False):
        if stderr.strip():
            logit(msg, "error")
            logit(stderr, "error")
            logit(stdout, "error")

            # Alert us of the provisioning error so we can response to it
            if email:
                send_terraform_provisioning_error(
                    self.app_config,
                    aws_account_data.get("account_id", "NO AWS ACCOUNT ID"),
                    str(stderr)
                )

            if throw:
                raise Exception(msg)

            return False

        return True

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
            msg = "Performing 'terraform plan' to AWS account {}..."
            logit(msg.format(aws_account_data['account_id']))

            refresh_state = str(bool(refresh_terraform_state)).lower()

            # Terraform plan
            process_handler = popen_communicate([
                temporary_directory + "terraform",
                "plan",
                "-refresh=" + refresh_state,
                "-var-file",
                join(temporary_directory, CUSTOMER_CONFIG_JSON)
            ], temporary_directory)

            process_stdout, process_stderr = process_handler.communicate()

            self.handle_terraform_result(
                "The 'terraform plan' has failed",
                process_stderr,
                process_stdout,
                aws_account_data,
                throw=True
            )
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

    def get_aws_account_by_id(self, aws_account_id):
        dbsession = self.db_session_maker()
        current_aws_account = dbsession.query(AWSAccount).filter(
            AWSAccount.account_id == aws_account_id,
        ).first()
        current_aws_account_dict = current_aws_account.to_dict()
        dbsession.close()

        return current_aws_account_dict

    def mark_account_as_available(self, db, aws_account_id, provision_info):
        aws_account = db.query(AWSAccount).filter(
            AWSAccount.account_id == aws_account_id,
        ).first()

        # Update the AWS account with this new information
        aws_account.redis_hostname = provision_info["redis_hostname"]
        aws_account.terraform_state = provision_info["terraform_state"]
        aws_account.ssh_public_key = provision_info["ssh_public_key"]
        aws_account.ssh_private_key = provision_info["ssh_private_key"]
        aws_account.aws_account_status = "AVAILABLE"

        return aws_account

    def create_terraform_state_version(self, provision_info, aws_account):
        terraform_state_version = TerraformStateVersion()
        terraform_state_version.terraform_state = provision_info["terraform_state"]
        aws_account.terraform_state_versions.append(
            terraform_state_version
        )

        return terraform_state_version

    def terraform_apply_aged_account(self, aws_account_id):
        msg = 'Kicking off terraform set-up for AWS account "{}"...'
        self.logger(msg.format(aws_account_id))
        aws_account_dict = self.get_aws_account_by_id(aws_account_id)

        try:
            # TODO make direct call instead?
            provision_info = yield self.task_spawner.terraform_configure_aws_account(
                aws_account_dict
            )

            self.logger(
                'Adding AWS account to the database'
                'the pool of "AVAILABLE" accounts...'
            )

            dbsession = self.db_session_maker()

            aws_account = self.mark_account_as_available(dbsession, aws_account_id, provision_info)
            terraform_state_version = self.create_terraform_state_version(provision_info, aws_account)
        except Exception as e:
            msg = 'Error occurred while provisioning AWS account "{}" with terraform!'
            self.logger(msg.format(aws_account.account_id), "error")
            self.logger(e)
            print_exc()
            self.logger("Marking the account as 'CORRUPT'...")

            # Provision failed, mark the account as corrupt
            aws_account.aws_account_status = "CORRUPT"

        msg = 'Commiting new account state of "{}" to database...'
        self.logger(msg.format(aws_account.aws_account_status))
        dbsession.add(terraform_state_version)
        dbsession.add(aws_account)
        dbsession.commit()

        self.logger("Freezing the account until it's used by someone...")

        self.task_spawner.freeze_aws_account(aws_account.to_dict())

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

        # Kick off the terraform apply jobs for aged accounts
        for aws_account_id in aws_account_ids:
            self.terraform_apply_aged_account(aws_account_id)

        # Create sub-accounts and let them age before applying terraform
        for i in range(0, accounts_to_create):
            self.create_sub_account_for_later_use()
