from pidgeon.service.block_state import BlockState
from pidgeon.gateway.dict_kv import DictKv
from pytest import fixture, raises, mark
from uuid import uuid4


class TestBlockState:
    @fixture
    def service(self):
        return BlockState(DictKv())

    @mark.asyncio
    async def test_ops_cycle(self, service):
        scenarios = [
            (str(uuid4()), str(uuid4()), str(uuid4()))
            for _ in range(100)
        ]

        for user_uuid, execution_id, data in scenarios:
            await service.set_block_result(user_uuid, execution_id, data)
            result = await service.get_block_result(user_uuid, execution_id)

            assert result == data

            await service.delete_block_result(user_uuid, execution_id)

            with raises(Exception):
                await service.get_block_result(user_uuid, execution_id)
