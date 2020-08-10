from asyncpg import create_pool
from json import dumps, loads
from pidgeon.framework.component.gateway import Gateway
from pinject import copy_args_to_public_fields
from time import time


CREATE_BLOCK_RESULT = """
CREATE TABLE IF NOT EXISTS block_result (
    key STRING PRIMARY KEY,
    val STRING NOT NULL,
    created INT NOT NULL
)
"""
PUT_QUERY = "INSERT INTO block_result (key, val, created) VALUES ($1, $2, $3)"
GET_QUERY = "SELECT (val) FROM block_result WHERE key = $1"


class CockroachKV(Gateway):
    _pool = None

    @copy_args_to_public_fields
    def __init__(self, config):
        self.user = config.get("cockroach_user")
        self.host = config.get("cockroach_host")
        self.port = config.get("cockroach_port")
        self.db = config.get("cockroach_db")

    async def get_pool(self):
        if not self._pool:
            self._pool = await create_pool(
                user=self.user,
                database=self.db,
                host=self.host,
                port=self.port
            )

            async with self._pool.acquire() as con:
                await con.execute(CREATE_BLOCK_RESULT)

        return self._pool

    async def put(self, key, value):
        pool = await self.get_pool()

        async with pool.acquire() as con:
            await con.execute(PUT_QUERY, key, dumps(value), int(time()))

    async def get(self, key):
        pool = await self.get_pool()

        async with pool.acquire() as con:
            result = await con.fetchrow(GET_QUERY, key)

        if result is not None:
            return loads(result[0])

    async def put_queue(self, key, value, index):
        pass

    async def pop_queue(self, key, value, index):
        pass

    async def delete(self, key):
        pass
