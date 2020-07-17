from json import loads
from pidgeon.exc import AuthError
from pidgeon.framework.component.service import Service
from pinject import copy_args_to_public_fields


class Auth(Service):
    config = None
    aws_secrets = None
    sym_crypto = None
    _block_result_key = None

    @copy_args_to_public_fields
    def __init__(self, config, aws_secrets, sym_crypto):
        pass

    async def _get_block_result_key(self):
        if self._block_result_key is None:
            self._block_result_key = await self.aws_secrets.get_block_result_key()

        return self._block_result_key

    async def authorize_block_result(self, auth):
        key = await self._get_block_result_key()
        auth = loads(self.sym_crypto.decrypt(key, auth))
        deployment_id = auth['deployment_id']

        if not deployment_id:
            raise AuthError("Unauthorized block storage access operation")

        return deployment_id
