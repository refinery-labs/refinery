from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
from utils.general import get_urand_password


ASSUME_ROLE_POLICY_DOC = """
{
"Version": "2012-10-17",
"Statement": [
	{
		"Sid": "",
		"Effect": "Allow",
		"Principal": {
			"Service": "lambda.amazonaws.com"
		},
		"Action": "sts:AssumeRole"
	}
]
}
"""


def create_third_party_aws_lambda_execute_role(aws_client_factory, credentials):
    # Create IAM client
    iam_client = aws_client_factory.get_aws_client(
        "iam",
        credentials
    )

    # Create the AWS role for the account
    response = iam_client.create_role(
        RoleName=THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME,
        Description="The role that all Lambdas deployed with Refinery run as",
        MaxSessionDuration=(60 * 60),
        AssumeRolePolicyDocument=ASSUME_ROLE_POLICY_DOC
    )

    response = iam_client.attach_role_policy(
        RoleName=THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
    )

    return True


def get_assume_role_credentials(app_config, sts_client, aws_account_id, session_lifetime):
    # Generate ARN for the sub-account AWS administrator role
    sub_account_admin_role_arn = "arn:aws:iam::" + \
        str(aws_account_id) + ":role/" + \
        app_config.get("customer_aws_admin_assume_role")

    # Session lifetime must be a minimum of 15 minutes
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html#STS.Client.assume_role
    min_session_lifetime_seconds = 900
    if session_lifetime < min_session_lifetime_seconds:
        session_lifetime = min_session_lifetime_seconds

    role_session_name = "Refinery-Managed-Account-Support-" + get_urand_password(12)

    response = sts_client.assume_role(
        RoleArn=sub_account_admin_role_arn,
        RoleSessionName=role_session_name,
        DurationSeconds=session_lifetime
    )

    return {
        "access_key_id": response["Credentials"]["AccessKeyId"],
        "secret_access_key": response["Credentials"]["SecretAccessKey"],
        "session_token": response["Credentials"]["SessionToken"],
        "expiration_date": response["Credentials"]["Expiration"],
        "assumed_role_id": response["AssumedRoleUser"]["AssumedRoleId"],
        "role_session_name": role_session_name,
        "arn": response["AssumedRoleUser"]["Arn"],
    }
