from pidgeon.framework.component.service import Service
from pinject import copy_args_to_public_fields


class BlockState(Service):
    sqlite_kv = None

    @copy_args_to_public_fields
    def __init__(self, sqlite_kv):
        pass

    @property
    def db(self):
        return self.sqlite_kv

    async def set_block_result(self, user_uuid, execution_id, data):
        await self.db.put(f"{user_uuid}-{execution_id}", data)

    async def get_block_result(self, user_uuid, execution_id):
        return await self.db.get(f"{user_uuid}-{execution_id}")

    async def delete_block_result(self, user_uuid, execution_id):
        await self.db.delete(f"{user_uuid}-{execution_id}")
