from pidgeon.framework.controller import Controller, handle


class HealthController(Controller):
    @handle("/health")
    async def test_fn(self):
        return {"alive": True}
