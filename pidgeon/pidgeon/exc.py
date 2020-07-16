from pidgeon.framework.exc import ApplicationError


class TestError(ApplicationError):
    code = 1


class AuthError(ApplicationError):
    code = 2
