from deployment.base import Builder
from deployment.serverless.module_builder import ServerlessModuleBuilder


class ServerlessBuilder(Builder):
    def __init__(self, app_config, aws_client_factory, project_id, deployment_id, project_config):
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.project_id = project_id
        self.deployment_id = deployment_id
        self.project_config = project_config

    def build(self):
        module_builder = ServerlessModuleBuilder(
            self.app_config,
            self.aws_client_factory,
            self.project_id,
            self.deployment_id,
            self.project_config
        )

        zipfile = module_builder.build()

    def teardown(self):
        pass