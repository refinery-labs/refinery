from tornado.concurrent import futures
import tornado

from tasks.build.temporal.nodejs import NodeJsBuilder
from tasks.build.temporal.python import PythonBuilder


class CodeBuilderFactory:
    # noinspection PyUnresolvedReferences
    def __init__(self, app_config, aws_client_factory, loop=None):
        self.executor = futures.ThreadPoolExecutor(10)
        self.loop = loop or tornado.ioloop.IOLoop.current()

        self.app_config = app_config
        self.aws_client_factory = aws_client_factory

    def get_nodejs12_builder(self, credentials, code, libraries):
        return NodeJsBuilder(
            self.executor,
            self.loop,
            self.app_config,
            self.aws_client_factory,
            credentials,
            code,
            libraries
        )

    def get_python36_builder(self, credentials, code, libraries):
        return PythonBuilder(
            self.executor,
            self.loop,
            self.app_config,
            self.aws_client_factory,
            credentials,
            code,
            libraries
        )
