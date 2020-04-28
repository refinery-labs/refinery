class InvalidOAuthOperationError(Exception):
    pass


class DuplicateOAuthUserCreationError(Exception):
    def __init__(self, email, provider):
        message = "Duplicate user creation attempt for " + provider + "with user " + email

        super(Exception, self).__init__(message)

        self.email = email
        self.provider = provider
