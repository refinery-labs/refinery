from deployment.serverless.builder import ServerlessBuilder
from tornado.concurrent import futures
import tornado


class BuilderFactory:
    # noinspection PyUnresolvedReferences
    def __init__(self, app_config, aws_client_factory, loop=None):
        self.executor = futures.ThreadPoolExecutor(10)
        self.loop = loop or tornado.ioloop.IOLoop.current()

        self.app_config = app_config
        self.aws_client_factory = aws_client_factory

    def get_serverless_builder(self, credentials, project_id, new_deployment_id, previous_build_id, diagram_data):
        return ServerlessBuilder(
            self.app_config,
            self.aws_client_factory,
            self.executor,
            self.loop,
            credentials,
            project_id,
            new_deployment_id,
            previous_build_id,
            diagram_data
        )
