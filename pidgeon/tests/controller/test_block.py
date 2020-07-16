from json import dumps
from pidgeon.controller.block import Block
from pidgeon.gateway.dict_kv import DictKv
from pidgeon.service.block_state import BlockState
from pidgeon.service.crypto import SymCrypto
from pytest import fixture, raises, mark
from uuid import uuid4


class TestBlock:
    @fixture
    def controller(self):
        config = {"block_result_key": SymCrypto.keygen()}
        block_state = BlockState(DictKv())
        sym_crypto = SymCrypto()

        return Block(config, block_state, sym_crypto)

    @mark.asyncio
    async def test_ops_cycle(self, controller):
        scenarios = [
            (str(uuid4()), str(uuid4()), str(uuid4()), str(uuid4()))
            for _ in range(100)
        ]

        for user_uuid, execution_id, result_id, data in scenarios:
            auth = self._get_auth(
                user_uuid,
                execution_id,
                controller.config['block_result_key'],
                controller.sym_crypto
            )
            data = str(uuid4())
            # Put
            await controller.set_block_state(auth, user_uuid, execution_id, result_id, data)
            # Get
            result = await controller.get_block_state(auth, user_uuid, execution_id, result_id)

            assert result == data
            # Delete
            await controller.delete_block_state(auth, user_uuid, execution_id, result_id)

            # Get and fail
            with raises(Exception):
                await controller.get_block_state(auth, user_uuid, execution_id, result_id)

    def test_validate_key_mismatch(self, controller):
        pass

    def _get_auth(self, user_uuid, execution_id, key, sym_crypto):
        auth = {"user_uuid": user_uuid, "execution_id": execution_id}
        return sym_crypto.encrypt(key, dumps(auth))
