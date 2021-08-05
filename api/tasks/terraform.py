import json
import shutil
from copy import copy
from json import loads
from shutil import rmtree
from subprocess import Popen, PIPE
from tasks.email import send_terraform_provisioning_error
from tasks.role import get_assume_role_credentials
from uuid import uuid4
from utils.general import logit


TERRAFORM_TIMEOUT = 300  # 5 minutes


def write_terraform_base_files(app_config, sts_client, aws_account_dict):
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

        return _write_terraform_base_files(
            app_config,
            sts_client,
            aws_account_dict,
            temporary_dir
        )
    except Exception as e:
        logit("An exception occurred while writing terraform base files for AWS account ID " +
              aws_account_dict["account_id"] + "\n" + repr(e), message_type="error")

        # Delete the temporary directory reguardless.
        rmtree(temporary_dir)

        raise


# TODO rename this
def _write_terraform_base_files(app_config, sts_client, aws_account_data, base_dir):
    logit("Setting up the base Terraform files (AWS Acc. ID '" +
          aws_account_data["account_id"] + "')...")

    # Get some temporary assume role credentials for the account
    assumed_role_credentials = get_assume_role_credentials(
        app_config,
        sts_client,
        str(aws_account_data["account_id"]),
        3600  # One hour - TODO CHANGEME
    )

    sub_account_admin_role_arn = "arn:aws:iam::" + \
        str(aws_account_data["account_id"]) + ":role/" + \
        app_config.get("customer_aws_admin_assume_role")

    # Write out the terraform configuration data
    terraform_configuration_data = {
        "session_token": assumed_role_credentials["session_token"],
        "role_session_name": assumed_role_credentials["role_session_name"],
        "assume_role_arn": sub_account_admin_role_arn,
        "access_key": assumed_role_credentials["access_key_id"],
        "secret_key": assumed_role_credentials["secret_access_key"],
        "region": app_config.get("region_name"),
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


def terraform_configure_aws_account(aws_client_factory, app_config, preterraform_manager, sts_client, aws_account_data):
    logit("Ensuring existence of ECS service-linked role before continuing with AWS account configuration...")
    preterraform_manager._ensure_ecs_service_linked_role_exists(
        aws_client_factory,
        aws_account_data
    )

    terraform_configuration_data = write_terraform_base_files(
        app_config,
        sts_client,
        aws_account_data
    )
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
            cwd=base_dir,
        )
        process_stdout, process_stderr = run_terraform_process(process_handler)

        if process_stderr.strip():
            logit("The Terraform provisioning has failed!", "error")
            logit(process_stderr, "error")
            logit(process_stdout, "error")

            # Alert us of the provisioning error so we can get ahead of
            # it with AWS support.
            send_terraform_provisioning_error(
                app_config,
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
            cwd=base_dir,
        )
        process_stdout, process_stderr = run_terraform_process(process_handler)

        # Parse Terraform JSON output
        terraform_provisioned_account_details = loads(
            process_stdout
        )

        logit("Pulled Terraform output successfully.")

        # Pull the terraform state and pull it so we can later
        # make terraform changes to user accounts.
        terraform_state = ""
        with open(base_dir + "terraform.tfstate", "r") as file_handler:
            terraform_state = file_handler.read()

        terraform_configuration_data["terraform_state"] = terraform_state
        terraform_configuration_data["redis_hostname"] = "FAKE_HOST" # terraform_provisioned_account_details["redis_elastic_ip"]["value"]
        terraform_configuration_data["ssh_public_key"] = terraform_provisioned_account_details[
            "refinery_redis_ssh_key_public_key_openssh"]["value"]
        terraform_configuration_data["ssh_private_key"] = terraform_provisioned_account_details[
            "refinery_redis_ssh_key_private_key_pem"]["value"]
    finally:
        # Ensure we clear the temporary directory no matter what
        rmtree(base_dir)

    return terraform_configuration_data


def terraform_apply(aws_client_factory, app_config, preterraform_manager, sts_client, aws_account_data, refresh_terraform_state):
    """
    This applies the latest terraform config to an account.

    THIS IS DANGEROUS, MAKE SURE YOU DID A FLEET TERRAFORM PLAN
    FIRST. NO EXCUSES, THIS IS ONE OF THE FEW WAYS TO BREAK PROD
    FOR OUR CUSTOMERS.

    -mandatory

    :param: refresh_terraform_state This value tells Terraform if it should refresh the state before running plan
    """

    logit("Ensuring existence of ECS service-linked role before continuing with terraform apply...")
    preterraform_manager._ensure_ecs_service_linked_role_exists(
        aws_client_factory,
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

    terraform_configuration_data = write_terraform_base_files(
        app_config,
        sts_client,
        aws_account_data
    )
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
            cwd=temporary_directory,
        )
        process_stdout, process_stderr = run_terraform_process(process_handler)
        return_data["stdout"] = process_stdout
        return_data["stderr"] = process_stderr

        # Pull the latest terraform state and return it
        # We need to do this regardless of if an error occurred.
        with open(temporary_directory + "terraform.tfstate", "r") as file_handler:
            return_data["new_tfstate"] = file_handler.read()

        if process_stderr.strip():
            logit("The 'terraform apply' has failed!", "error")
            logit(process_stderr, "error")
            logit(process_stdout, "error")

            # Alert us of the provisioning error so we can response to it
            send_terraform_provisioning_error(
                app_config,
                aws_account_data["account_id"],
                str(process_stderr)
            )

            return_data["success"] = False
    finally:
        # Ensure we clear the temporary directory no matter what
        rmtree(temporary_directory)

    logit("'terraform apply' completed, returning results...")

    return return_data


def terraform_plan(app_config, sts_client, aws_account_data, refresh_terraform_state):
    """
    This does a terraform plan to an account and sends an email
    with the results. This allows us to see the impact of a new
    terraform change before we roll it out across our customer's
    AWS accounts.
    :param: refresh_terraform_state This value tells Terraform if it should refresh the state before running plan
    """

    terraform_configuration_data = write_terraform_base_files(
        app_config,
        sts_client,
        aws_account_data
    )
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
            cwd=temporary_directory,
        )
        process_stdout, process_stderr = run_terraform_process(process_handler)

        if process_stderr.strip():
            logit("The 'terraform plan' has failed!", "error")
            logit(process_stderr, "error")
            logit(process_stdout, "error")

            raise Exception("Terraform plan failed.")
    finally:
        # Ensure we clear the temporary directory no matter what
        rmtree(temporary_directory)

    logit("Terraform plan completed successfully, returning output.")

    return process_stdout


def run_terraform_process(process):
    return process.communicate(timeout=TERRAFORM_TIMEOUT)
