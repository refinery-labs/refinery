class DuplicateUserCreationError(Exception):
    def __init__(self, message, code):
        super(Exception, self).__init__(message)

        self.code = code
