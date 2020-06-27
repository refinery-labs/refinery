class AlreadyInvokedException(Exception):
    def __init__(self, message="This function has already been invoked!"):
        # Call the base class constructor with the parameters it needs
        super(AlreadyInvokedException, self).__init__(message)


class InvokeQueueEmptyException(Exception):
    def __init__(self, message="We've exhausted all of the invocations we have to do!"):
        # Call the base class constructor with the parameters it needs
        super(InvokeQueueEmptyException, self).__init__(message)
