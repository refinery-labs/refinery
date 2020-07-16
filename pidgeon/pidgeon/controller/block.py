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
    async def get_block_state(self, auth, user_uuid, execution_id, result_id):
        self._validate_key(user_uuid, execution_id, auth)
        return await self.block_state.get_block_result(user_uuid, execution_id, result_id)

    @handle("/block/state/set")
    async def set_block_state(self, auth, user_uuid, execution_id, result_id, data):
        self._validate_key(user_uuid, execution_id, auth)
        await self.block_state.set_block_result(user_uuid, execution_id, result_id, data)

    @handle("/block/state/delete")
    async def delete_block_state(self, auth, user_uuid, execution_id, result_id):
        self._validate_key(user_uuid, execution_id, auth)
        await self.block_state.delete_block_result(user_uuid, execution_id, result_id)

    def _validate_key(self, user_uuid, execution_id, enc_auth):
        auth = loads(self.sym_crypto.decrypt(self.key, enc_auth))
        auth_user_uuid = auth['user_uuid']
        auth_execution_id = auth['execution_id']

        if user_uuid != auth_user_uuid or execution_id != auth_execution_id:
            raise AuthError("Unauthorized block storage access operation")
