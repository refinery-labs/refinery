from json import dumps, loads
from pidgeon.framework.component.gateway import Gateway
from pinject import copy_args_to_public_fields
from sqlite3 import connect


CREATE_QUERY = """
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""
PUT_QUERY = "INSERT INTO kv (key, value) VALUES (?, ?)"
GET_QUERY = "SELECT value FROM kv WHERE key = ? LIMIT 1"
DELETE_QUERY = "DELETE FROM kv WHERE key = ?"


class SqliteKv(Gateway):
    @copy_args_to_public_fields
    def __init__(self, config):
        self.conn = connect(config.get("sqlite_kv_path"))
        self.conn.execute(CREATE_QUERY)

    async def put(self, key, value):
        self.conn.execute(PUT_QUERY, (key, dumps(value)))

    async def get(self, key):
        cursor = self.conn.cursor()
        cursor.execute(GET_QUERY, (key,))
        result, = cursor.fetchone()

        return loads(result)

    async def delete(self, key):
        self.conn.execute(DELETE_QUERY, (key,))
