from pidgeon.framework.component.gateway import Gateway


class DictKv(Gateway):
    def __init__(self):
        self.mapper = {}

    async def put(self, key, value):
        self.mapper[key] = value

    async def get(self, key):
        return self.mapper[key]

    async def delete(self, key):
        del self.mapper[key]
