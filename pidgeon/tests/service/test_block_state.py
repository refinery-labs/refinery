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
            (str(uuid4()), str(uuid4()), str(uuid4()), str(uuid4()))
            for _ in range(100)
        ]

        for deployment_id, execution_id, result_id, data in scenarios:
            await service.set_block_result(deployment_id, execution_id, result_id, data)
            result = await service.get_block_result(deployment_id, execution_id, result_id)

            assert result == data

            await service.delete_block_result(deployment_id, execution_id, result_id)

            with raises(Exception):
                await service.get_block_result(deployment_id, execution_id, result_id)