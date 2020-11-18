from data_types.aws_api_gateway_config import AwsApiGatewayConfig
from resources.base import Resource
from tasks.api_gateway import create_resource


class AWSAPIEndpoint(Resource):
    def __init__(self, credentials, config: AwsApiGatewayConfig):
        self.credentials = credentials
        self.config = config

    def deploy(self):
        return create_resource(
            self.credentials,
            self.config.gateway_id,
            self.config.parent_id,
            self.config.path_part
        )

    def teardown(self):
        pass

    def uid(self):
        return self.config.uid
