from aiobotocore import get_session
from json import loads
from pidgeon.exc import SecretsError
from pidgeon.framework.component.gateway import Gateway


SERVICE_NAME = "secretsmanager"


class AwsSecrets(Gateway):
    def __init__(self, config):
        self._secret_access_key = config.get("aws_secret_access_key")
        self._access_key_id = config.get("aws_access_key_id")
        self._aws_region = config.get("aws_region")
        self._block_result_secret_id = config.get("block_result_secret_id")
        self._block_result_secret_key = config.get("block_result_secret_key")

    def get_client(self):
        session = get_session()
        return session.create_client(
            SERVICE_NAME,
            region_name=self._aws_region,
            aws_secret_access_key=self._secret_access_key,
            aws_access_key_id=self._access_key_id
        )

    async def get(self, secret_id):
        async with self.get_client() as client:
            response = await client.get_secret_value(
                SecretId=secret_id,
            )

        if 'SecretString' not in response:
            raise SecretsError(f"No such secret {secret_id}")

        return loads(response['SecretString'])

    async def get_block_result_key(self):
        secret = await self.get(self._block_result_secret_id)

        if self._block_result_secret_key not in secret:
            err = 'Secret {} has no key {}'
            raise SecretsError(err.format(
                self._block_result_secret_id,
                self._block_result_secret_key
            ))

        return secret[self._block_result_secret_key]
