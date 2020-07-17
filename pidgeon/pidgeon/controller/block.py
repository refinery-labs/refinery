from json import loads
from pidgeon.exc import AuthError
from pidgeon.framework.component.controller import Controller, handle
from pinject import copy_args_to_public_fields


class Block(Controller):
    config = None
    block_state = None
    sym_crypto = None

    @copy_args_to_public_fields
    def __init__(self, config, block_state, sym_crypto):
        self.key = config.get("block_result_key")

    @handle("/block/state/get")
    async def get_block_state(self, auth, execution_id, result_id):
        deployment_id = self._validate_key(auth)
        return await self.block_state.get_block_result(deployment_id, execution_id, result_id)

    @handle("/block/state/set")
    async def set_block_state(self, auth, execution_id, result_id, data):
        deployment_id = self._validate_key(auth)
        await self.block_state.set_block_result(deployment_id, execution_id, result_id, data)

    @handle("/block/state/delete")
    async def delete_block_state(self, auth, execution_id, result_id):
        deployment_id = self._validate_key(auth)
        await self.block_state.delete_block_result(deployment_id, execution_id, result_id)

    def _validate_key(self, auth):
        auth = loads(self.sym_crypto.decrypt(self.key, auth))
        deployment_id = auth['deployment_id']

        if not deployment_id:
            raise AuthError("Unauthorized block storage access operation")

        return deployment_id
