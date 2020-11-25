from deployment.base import Builder
from deployment.serverless.module_builder import ServerlessModuleBuilder
from functools import cached_property
from tasks.build.common import get_codebuild_artifact_zip_data
from uuid import uuid4
from zipfile import ZipFile


class ServerlessBuilder(Builder):
    def __init__(self, app_config, aws_client_factory, project_id, deployment_id, project_config):
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.project_id = project_id
        self.deployment_id = deployment_id
        self.project_config = project_config

    @cached_property
    def codebuild(self):
        return self.aws_client_factory.get_aws_client(
            "codebuild",
            self.credentials
        )

    @cached_property
    def s3(self):
        return self.aws_client_factory.get_aws_client(
            "s3",
            self.credentials
        )

    @cached_property
    def s3_key(self):
        return f'buildspecs/{self.deployment_id}.zip'

    @cached_property
    def s3_path(self):
        return f"{self.credentials['lambda_packages_bucket']}/{self.s3_key}"

    @cached_property
    def s3_bucket(self):
        return self.credentials['lambda_packages_bucket']

    @cached_property
    def final_s3_package_zip_path(self):
        return f"{self.deployment_id}.zip"

    def build(self, rebuild=False):
        artifact_zip = self.get_artifact_zipfile() if rebuild else None
        module_builder = ServerlessModuleBuilder(
            self.app_config,
            self.aws_client_factory,
            self.project_id,
            self.deployment_id,
            self.project_config
        )
        zipfile = module_builder.build(artifact_zip)
        serverless_zipfile = self.perform_codebuild(zipfile)

        return self.parse_serverless_output(serverless_zipfile)

    def get_artifact_zipfile(self):
        return self.read_from_s3(
            self.aws_client_factory,
            self.credentials,
            self.s3_bucket,
            self.final_s3_package_zip_path
        )

    def perform_codebuild(self, zipfile):
        self.s3.put_object(
            Bucket=self.credentials['lambda_packages_bucket'],
            Body=zipfile,
            Key=self.s3_key,
            # Legacy indicates this value must be public read, this assertion
            # should be validated in the future.
            ACL="public-read"
        )

        build_id = self.codebuild.start_build(
            projectName='refinery-serverless-builds',
            sourceTypeOverride='s3',
            sourceLocationOverride=self.s3_path,
            imageOverride="aws/codebuild/nodejs:12"
        )['build']['id']

        return get_codebuild_artifact_zip_data(
            self.aws_client_factory,
            self.credentials,
            build_id,
            self.final_s3_package_zip_path
        )

    def parse_serverless_output(self, serverless_zipfile):
        # TODO return deployment.json created from project.json and serverless_info
        with ZipFile(serverless_zipfile) as zipfile:
            with zipfile.open('serverless_info') as serverless_info:
                print('----------------------------------------')
                print("SERVERLESS INFO")
                print(serverless_info.read())
                print('----------------------------------------')