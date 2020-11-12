from resources.base import Resource


class AWSLambda(Resource):
    def __init__(self, app_config, aws_client_factory, credentials):
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.credentials = credentials

    def serialize(self):
        pass

    def deploy(self):
        pass

    def teardown(self):
        pass