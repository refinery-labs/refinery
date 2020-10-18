

class LambdaTimeoutError(Exception):
    def __init__(self, lambda_object):
        self.lambda_object = lambda_object

