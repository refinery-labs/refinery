import pinject
from botocore.exceptions import ClientError

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory


class AwsSecretsManagerFactory:
    aws_client_factory: AwsClientFactory = None

    @pinject.copy_args_to_public_fields
    def __init__(self, aws_client_factory):
        pass

    def new_secrets_manager(self, credentials):
        return AwsSecretsManager(self.aws_client_factory, credentials)


class AwsSecretsManager:
    def __init__(self, aws_client_factory: AwsClientFactory, credentials):
        self.secrets_manager = aws_client_factory.get_aws_client(
            "secretsmanager",
            credentials
        )
        self.credentials = credentials

    def store_secret(self, name, secret_value):
        try:
            resp = self.secrets_manager.create_secret(
                Name=name,
                SecretBinary=secret_value
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code != "ResourceExistsException":
                raise e
            resp = self.secrets_manager.put_secret_value(
                SecretId=name,
                SecretBinary=secret_value
            )
            # fallthrough

        return resp.get('ARN')
