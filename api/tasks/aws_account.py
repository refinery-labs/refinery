from boto3 import Session
from botocore.exceptions import ClientError
from json import dumps
from models.aws_accounts import AWSAccount
from tasks.aws_lambda import get_lambda_arns
from tasks.ec2 import get_ec2_instance_ids
from tasks.role import get_assume_role_credentials
from time import sleep
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
    for _ in xrange(60):
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
        time.sleep(5)

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
    for _ in xrange(10):
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

def unfreeze_aws_account(aws_client_factory, credentials):
    """
    Unfreezes a previously-frozen AWS account, this is for situations
    where a user has gone over their free-trial or billing limit leading
    to their account getting frozen. By calling this the account will be
    re-enabled for regular Refinery use.
    * De-throttle all AWS Lambdas
    * Turn on EC2 instances (redis)
    """
    logit("Unfreezing AWS account...")

    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    ec2_client = aws_client_factory.get_aws_client(
        "ec2",
        credentials
    )

    # Pull all Lambda ARN(s)
    lambda_arns = get_lambda_arns(
        aws_client_factory,
        credentials
    )

    # Remove function throttle from each Lambda
    for lambda_arn in lambda_arns:
        lambda_client.delete_function_concurrency(
            FunctionName=lambda_arn
        )

    # Start EC2 instance(s)
    ec2_instance_ids = get_ec2_instance_ids(
        aws_client_factory, credentials)

    # Max attempts
    remaining_attempts = 20

    # Prevents issue if a freeze happens too quickly after an un-freeze
    while remaining_attempts > 0:
        try:
            start_instance_response = ec2_client.start_instances(
                InstanceIds=ec2_instance_ids
            )
        except ClientError as boto_error:
            if boto_error.response["Error"]["Code"] != "IncorrectInstanceState":
                raise

            logit("EC2 instance isn't ready to be started yet!")
            logit("Waiting 2 seconds and trying again...")
            sleep(2)

        remaining_attempts = remaining_attempts - 1

    return True


def freeze_aws_account(app_config, aws_client_factory, db_session_maker, credentials):
    """
    Freezes an AWS sub-account when the user has gone past
    their free trial or when they have gone tardy on their bill.

    This is different from closing an AWS sub-account in that it preserves
    the underlying resources in the account. Generally this is the
    "warning shot" before we later close the account and delete it all.

    The steps are as follows:
    * Disable AWS console access by changing the password
    * Revoke all active AWS console sessions - TODO
    * Iterate over all deployed Lambdas and throttle them
    * Stop all active CodeBuilds
    * Turn-off EC2 instances (redis)
    """
    logit("Freezing AWS account...")

    iam_client = aws_client_factory.get_aws_client(
        "iam",
        credentials
    )

    lambda_client = aws_client_factory.get_aws_client(
        "lambda",
        credentials
    )

    codebuild_client = aws_client_factory.get_aws_client(
        "codebuild",
        credentials
    )

    ec2_client = aws_client_factory.get_aws_client(
        "ec2",
        credentials
    )

    # Rotate and log out users from the AWS console
    new_console_user_password = recreate_aws_console_account(
        app_config,
        aws_client_factory,
        credentials,
        True
    )

    # Update the console login in the database
    dbsession = db_session_maker()
    aws_account = dbsession.query(AWSAccount).filter_by(
        account_id=credentials["account_id"]
    ).first()
    aws_account.iam_admin_password = new_console_user_password
    dbsession.commit()

    # Get Lambda ARNs
    lambda_arn_list = get_lambda_arns(aws_client_factory, credentials)

    # List all CodeBuild builds and stop any that are running
    codebuild_build_ids = []
    codebuild_list_params = {}

    # Bound this loop to only execute MAX_LOOP_ITERATION times
    for _ in xrange(1000):
        codebuild_list_response = codebuild_client.list_builds(
            **codebuild_list_params
        )

        for build_id in codebuild_list_response["ids"]:
            codebuild_build_ids.append(
                build_id
            )

        if not ("nextToken" in codebuild_list_response):
            break

        codebuild_list_params["nextToken"] = codebuild_list_response["nextToken"]

    # We now scan these builds to see if they are currently running.
    # We can do this in batches of 100
    active_build_ids = []
    chunk_size = 100

    while len(codebuild_build_ids) > 0:
        chunk_of_build_ids = codebuild_build_ids[:chunk_size]
        remaining_build_ids = codebuild_build_ids[chunk_size:]
        codebuild_build_ids = remaining_build_ids

        # Pull the information for the build ID chunk
        builds_info_response = codebuild_client.batch_get_builds(
            ids=chunk_of_build_ids,
        )

        # Iterate over the builds info response to find live build IDs
        for build_info in builds_info_response["builds"]:
            if build_info["buildStatus"] == "IN_PROGRESS":
                active_build_ids.append(
                    build_info["id"]
                )

    # Run through all active builds and stop them in their place
    for active_build_id in active_build_ids:
        stop_build_response = codebuild_client.stop_build(
            id=active_build_id
        )

    ec2_instance_ids = get_ec2_instance_ids(
        aws_client_factory, credentials)

    stop_instance_response = ec2_client.stop_instances(
        InstanceIds=ec2_instance_ids
    )

    dbsession.close()
    return False

def recreate_aws_console_account(app_config, aws_client_factory, credentials, rotate_password, force_continue=False):
    iam_client = aws_client_factory.get_aws_client(
        "iam",
        credentials
    )

    # The only way to revoke an AWS Console user's session
    # is to delete the console user and create a new one.

    # Generate the IAM policy ARN
    iam_policy_arn = "arn:aws:iam::" + \
        credentials["account_id"] + ":policy/RefineryCustomerPolicy"

    logit("Deleting AWS console user...")

    # TODO check responses from these calls?

    try:
        # Delete the current AWS console user
        delete_user_profile_response = iam_client.delete_login_profile(
            UserName=credentials["iam_admin_username"],
        )

        # Remove the policy from the user
        detach_user_policy = iam_client.detach_user_policy(
            UserName=credentials["iam_admin_username"],
            PolicyArn=iam_policy_arn
        )

        # Delete the IAM user
        delete_user_response = iam_client.delete_user(
            UserName=credentials["iam_admin_username"],
        )
    except Exception as e:
        logit("Unable to delete IAM user during recreate process")

        # Raise the exception again unless the flag is set to force continuation
        if force_continue is False:
            raise e

    logit("Re-creating the AWS console user...")

    # Create the IAM user again
    delete_user_response = iam_client.create_user(
        UserName=credentials["iam_admin_username"],
    )

    # Create the IAM user again
    delete_policy_response = iam_client.delete_policy(
        PolicyArn=iam_policy_arn
    )

    # Create IAM policy for the user
    create_policy_response = iam_client.create_policy(
        PolicyName="RefineryCustomerPolicy",
        PolicyDocument=json.dumps(app_config.get("CUSTOMER_IAM_POLICY")),
        Description="Refinery Labs managed AWS customer account policy."
    )

    # Attach the limiting IAM policy to it.
    attach_policy_response = iam_client.attach_user_policy(
        UserName=credentials["iam_admin_username"],
        PolicyArn=iam_policy_arn
    )

    # Generate a new user console password
    new_console_user_password = get_urand_password(32)

    if rotate_password == False:
        new_console_user_password = credentials["iam_admin_password"]

    # Create the console user again.
    create_user_response = iam_client.create_login_profile(
        UserName=credentials["iam_admin_username"],
        Password=new_console_user_password,
        PasswordResetRequired=False
    )

    return new_console_user_password


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
