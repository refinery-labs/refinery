from json import dumps
from pidgeon.controller.block import Block
from pidgeon.gateway.dict_kv import DictKv
from pidgeon.service.block_state import BlockState
from pidgeon.service.crypto import SymCrypto
from pytest import fixture, raises, mark
from uuid import uuid4


class MockAuth:
    def __init__(self, deployment_id):
        self.deployment_id = deployment_id

    async def authorize_block_result(self, auth):
        return self.deployment_id


class TestBlock:
    @fixture
    def controller(self):
        config = {"block_result_key": SymCrypto.keygen()}
        block_state = BlockState(DictKv())
        auth = MockAuth(str(uuid4()))
        sym_crypto = SymCrypto()

        return Block(config, block_state, sym_crypto, auth)

    @mark.asyncio
    async def test_ops_cycle(self, controller):
        deployment_id = controller.auth.deployment_id
        scenarios = [
            (str(uuid4()), str(uuid4()))
            for _ in range(100)
        ]

        for execution_id, data in scenarios:
            auth = self._get_auth(
                deployment_id,
                controller.config['block_result_key'],
                controller.sym_crypto
            )
            data = str(uuid4())
            # Put
            await controller.set_block_state(auth, execution_id, data)
            # Get
            result = await controller.get_block_state(auth, execution_id)

            assert result == data
            # Delete
            await controller.delete_block_state(auth, execution_id)

            # Get and fail
            with raises(Exception):
                await controller.get_block_state(auth, execution_id)

    def test_validate_key_mismatch(self, controller):
        pass

    def _get_auth(self, deployment_id, key, sym_crypto):
        auth = {"deployment_id": deployment_id}
        return sym_crypto.encrypt(key, dumps(auth))
