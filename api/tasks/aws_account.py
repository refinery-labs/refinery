import json

from boto3 import Session
from botocore.exceptions import ClientError
from json import dumps

from models import User, Organization
from models.aws_accounts import AWSAccount
from tasks.aws_lambda import get_lambda_arns
from tasks.ec2 import get_ec2_instance_ids
from tasks.role import get_assume_role_credentials
from utils.general import logit, get_urand_password
from time import sleep


def create_aws_org_sub_account(app_config, aws_organization_client, refinery_aws_account_id, email):
    account_name = "Refinery Customer Account " + refinery_aws_account_id

    response = aws_organization_client.create_account(
        Email=email,
        RoleName=app_config.get("customer_aws_admin_assume_role"),
        AccountName=account_name,
        IamUserAccessToBilling="DENY"
    )
    account_status_data = response["CreateAccountStatus"]
    create_account_id = account_status_data["Id"]

    # Loop while the account is being created (up to ~5 minutes)
    for _ in range(60):
        if account_status_data["State"] == "SUCCEEDED" and "AccountId" in account_status_data:
            return {
                "account_name": account_name,
                "account_id": account_status_data["AccountId"],
            }

        if account_status_data["State"] == "FAILED":
            logit("The account creation has failed!", "error")
            logit("Full account creation response is the following: ", "error")
            logit(account_status_data)
            return False

        logit("Current AWS account creation status is '" +
              account_status_data["State"] + "', waiting 5 seconds before checking again...")
        sleep(5)

        # Poll AWS again to see if the account creation has progressed
        response = aws_organization_client.describe_create_account_status(
            CreateAccountRequestId=create_account_id
        )
        account_status_data = response["CreateAccountStatus"]


def create_new_console_user(app_config, access_key_id, secret_access_key, session_token, username, password):
    # Create a Boto3 session with the assumed role credentials
    # This allows us to create a client which will be authenticated
    # as the account we assumed the role of.
    iam_session = Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token
    )

    # IAM client spawned from the assumed role session
    iam_client = iam_session.client("iam")

    # Create an IAM user
    create_user_response = iam_client.create_user(
        UserName=username
    )

    # Create IAM policy for the user
    create_policy_response = iam_client.create_policy(
        PolicyName="RefineryCustomerPolicy",
        PolicyDocument=dumps(app_config.get("CUSTOMER_IAM_POLICY")),
        Description="Refinery Labs managed AWS customer account policy."
    )

    # Attaches limited access policy to the AWS account to scope
    # down the permissions the Refinery customer can perform in
    # the AWS console.
    attach_policy_response = iam_client.attach_user_policy(
        UserName=username,
        PolicyArn=create_policy_response["Policy"]["Arn"]
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
        "arn": create_user_response["User"]["Arn"]
    }


def create_new_sub_aws_account(app_config, db_session_maker, aws_organization_client, sts_client, account_type, aws_account_id):
    # Create a unique ID for the Refinery AWS account
    aws_unique_account_id = get_urand_password(16).lower()

    # Store the AWS account in the database
    new_aws_account = AWSAccount()
    new_aws_account.account_label = ""
    new_aws_account.region = app_config.get("region_name")
    new_aws_account.s3_bucket_suffix = str(get_urand_password(32)).lower()
    new_aws_account.iam_admin_username = "refinery-customer"
    new_aws_account.iam_admin_password = get_urand_password(32)
    new_aws_account.redis_hostname = ""
    new_aws_account.redis_password = get_urand_password(64)
    new_aws_account.redis_port = 6379
    new_aws_account.redis_secret_prefix = get_urand_password(40)
    new_aws_account.terraform_state = ""
    new_aws_account.ssh_public_key = ""
    new_aws_account.ssh_private_key = ""
    new_aws_account.aws_account_email = app_config.get(
        "customer_aws_email_prefix") + aws_unique_account_id + app_config.get("customer_aws_email_suffix")
    new_aws_account.terraform_state_versions = []
    new_aws_account.aws_account_status = "CREATED"
    new_aws_account.account_type = account_type

    # Create AWS sub-account
    logit("Creating AWS sub-account '" +
          str(new_aws_account.aws_account_email) + "'...")

    # Only create a sub-account if this is a MANAGED AWS account and skip
    # this step if we're onboarding a THIRDPARTY AWS account (e.g. self-hosted)
    if account_type == "MANAGED":
        # Create sub-AWS account
        account_creation_response = create_aws_org_sub_account(
            app_config,
            aws_organization_client,
            aws_unique_account_id,
            str(new_aws_account.aws_account_email),
        )

        if account_creation_response == False:
            raise Exception("Account creation failed, quitting out!")

        new_aws_account.account_id = account_creation_response["account_id"]
        logit("Sub-account created! AWS account ID is " +
              new_aws_account.account_id + ".")
    elif account_type == "THIRDPARTY":
        new_aws_account.account_id = aws_account_id
        logit("Using provided AWS Account ID " +
              new_aws_account.account_id + ".")

    assumed_role_credentials = {}

    # Try to assume the role up to 10 times
    for _ in range(10):
        logit("Attempting to assume the sub-account's administrator role...")

        try:
            # We then assume the administrator role for the sub-account we created
            assumed_role_credentials = get_assume_role_credentials(
                app_config,
                sts_client,
                str(new_aws_account.account_id),
                3600  # One hour - TODO CHANGEME
            )
            break
        except ClientError as boto_error:
            logit("Assume role boto error:" + repr(boto_error), "error")
            # If it's not an AccessDenied exception it's not what we except so we re-raise
            if boto_error.response["Error"]["Code"] != "AccessDenied":
                logit("Unexpected Boto3 response: " +
                      boto_error.response["Error"]["Code"])
                logit(boto_error.response)
                raise boto_error

            # Otherwise it's what we accept and we just need to wait.
            logit(
                "Got an Access Denied error, role is likely not propogated yet. Trying again in 5 seconds...")
            sleep(5)

    logit("Successfully assumed the sub-account's administrator role.")
    logit("Minting a new AWS Console User account for the customer to use...")

    # Using the credentials from the assumed role we mint an IAM console
    # user for Refinery customers to use to log into their managed AWS account.
    create_console_user_results = create_new_console_user(
        app_config,
        assumed_role_credentials["access_key_id"],
        assumed_role_credentials["secret_access_key"],
        assumed_role_credentials["session_token"],
        str(new_aws_account.iam_admin_username),
        str(new_aws_account.iam_admin_password)
    )

    # Add AWS account to database
    dbsession = db_session_maker()
    dbsession.add(new_aws_account)
    dbsession.commit()
    dbsession.close()

    logit("New AWS account created successfully and stored in database as 'CREATED'!")

    return True


def do_account_cleanup(app_config, db_session_maker, aws_lambda_client):
    """
    When an account has been closed on refinery, the AWS account associated with it has gone stale.
    In order to prevent any future charges of this account, we close it out using a script which:
    1) Resets the root AWS account password (required to do anything with the account)
    2) Waits for the mailgun API to receive the email
    3) Logs into the root AWS account
    4) Marks account to be closed
    """
    delete_account_lambda_arn = app_config.get(
        "delete_account_lambda_arn")

    dbsession = db_session_maker()

    # find all organizations which have been marked as 'disabled'
    rows = dbsession.query(User, Organization, AWSAccount).filter(
        User.organization_id == Organization.id
    ).filter(
        Organization.id == AWSAccount.organization_id
    ).filter(
        AWSAccount.aws_account_status == "NEEDS_CLOSING",
        AWSAccount.account_type == "MANAGED"
    ).all()

    # load all of the results to be processed
    accounts = [
        (row[2].id, row[2].aws_account_email) for row in rows]
    dbsession.close()

    removed_accounts = 0
    for aws_account in accounts:
        account_id = aws_account[0]
        email = aws_account[1]

        response = aws_lambda_client.invoke(
            FunctionName=delete_account_lambda_arn,
            InvocationType="RequestResponse",
            LogType="Tail",
            Payload=json.dumps({
                "email": email
            })
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            logit("failed to remove account: " + email)
        else:
            # mark the account as closed
            dbsession = db_session_maker()
            account = dbsession.query(AWSAccount).filter(
                AWSAccount.id == account_id
            ).first()
            account.aws_account_status = "CLOSED"
            dbsession.commit()
            dbsession.close()

            removed_accounts += 1

    return removed_accounts


def mark_account_needs_closing(db_session_maker, email):
    dbsession = db_session_maker()

    row = dbsession.query(User, Organization, AWSAccount).filter(
        User.organization_id == Organization.id
    ).filter(
        Organization.id == AWSAccount.organization_id
    ).filter(
        AWSAccount.aws_account_status == "IN_USE",
        AWSAccount.account_type == "MANAGED",
        User.email == email
    ).first()

    if row is None:
        logit('unable to find user with email: ' + email)
        return False

    aws_account = row[2]
    aws_account.aws_account_status = "NEEDS_CLOSING"

    dbsession.commit()
    dbsession.close()

    return True
