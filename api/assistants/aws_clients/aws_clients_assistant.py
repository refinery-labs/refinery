import boto3
import pinject

from botocore.client import Config
from expiringdict import ExpiringDict
from utils.general import get_urand_password


class STSClientBindingSpec(pinject.BindingSpec):
    @pinject.provides("sts_client")
    def provide_sts_client(self, app_config):
        # This client is used to assume role into all of our customer's
        # AWS accounts as a root-priveleged support account ("DO_NOT_DELETE_REFINERY_SYSTEM_ACCOUNT")
        return boto3.client(
            "sts",
            aws_access_key_id=app_config.get("aws_access_key"),
            aws_secret_access_key=app_config.get("aws_secret_key"),
            region_name=app_config.get("region_name"),
            config=Config(
                max_pool_connections=(1000 * 2)
            )
        )


class AwsClientFactory:
    app_config = None
    sts_client = None

    _boto3_client_cache = None

    @pinject.copy_args_to_public_fields
    def __init__(self, app_config, sts_client):
        """
        This is some poor-man's caching to greately speed up Boto3
        client access times. We basically just cache and return the client
        if it's less than the STS Assume Role age.

        Basically this is critical when we do things like the S3 log pulling
        because it does TONS of concurrent connections. Without the caching it
        can take ~35 seconds to pull the logs, with the caching it takes ~5.
        """
        self._boto3_client_cache = ExpiringDict(
            max_len=500,
            max_age_seconds=(int(app_config.get("assume_role_session_lifetime_seconds")) - 60)
        )

    def get_aws_client(self, client_type, credentials):
        """
        Take an AWS client type ("s3", "lambda", etc) and utilize
        STS to assume role into the customer's account and return
        a key and token for the admin service account ("DO_NOT_DELETE_REFINERY_SYSTEM_ACCOUNT")
        """
        cache_key = client_type + credentials["account_id"] + credentials["region"]

        if cache_key in self._boto3_client_cache:
            return self._boto3_client_cache[cache_key]

        # Generate the Refinery AWS management role ARN we are going to assume into
        sub_account_admin_role_arn = "arn:aws:iam::" + credentials["account_id"] + ":role/DO_NOT_DELETE_REFINERY_SYSTEM_ACCOUNT"

        # We need to generate a random role session name
        role_session_name = "Refinery-Managed-Account-Support-" + get_urand_password(12)

        # Perform the assume role action
        assume_role_response = self.sts_client.assume_role(
            RoleArn=sub_account_admin_role_arn,
            RoleSessionName=role_session_name,
            DurationSeconds=int(self.app_config.get("assume_role_session_lifetime_seconds"))
        )

        # Remove non-JSON serializable part from response
        del assume_role_response["Credentials"]["Expiration"]

        # Take the assume role credentials and use it to create a boto3 session
        boto3_session = boto3.Session(
            aws_access_key_id=assume_role_response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=assume_role_response["Credentials"]["SecretAccessKey"],
            aws_session_token=assume_role_response["Credentials"]["SessionToken"],
            region_name=credentials["region"],
        )

        def inject_header(params, **kwargs):
            params["headers"]["Connection"] = "Keep-Alive"

        boto3_session.events.register("before-call.s3", inject_header)

        # Options for boto3 client
        client_options = {
            "config": Config(
                max_pool_connections=(250 * 1),
                connect_timeout=(60 * 10)  # For large files
            )
        }

        # Custom configurations depending on the client type
        if client_type == "lambda":
            client_options["config"] = Config(
                connect_timeout=50,
                read_timeout=(60 * 15),
                max_pool_connections=(1000 * 2)
            )

        # Use the new boto3 session to create a boto3 client
        boto3_client = boto3_session.client(
            client_type,
            **client_options
        )

        # Store it in the cache for future access
        self._boto3_client_cache[cache_key] = boto3_client

        return boto3_client
