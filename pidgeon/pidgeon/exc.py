from pidgeon.framework.exc import ApplicationError


###############################################################################
# Application Errors
###############################################################################


class TestError(ApplicationError):
    code = 1


class AuthError(ApplicationError):
    code = 2


###############################################################################
# All other exceptions (masked from end user)
###############################################################################


class SecretsError(Exception):
    pass
