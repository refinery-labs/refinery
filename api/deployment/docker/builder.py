from deployment.base import Builder
from deployment.docker.dockerfile_builder import DockerEnvBuilder
from deployment.serverless.deploy_config_builder import DeploymentConfigBuilder
from deployment.serverless.info_parser import ServerlessInfoParser
from deployment.serverless.module_builder import ServerlessModuleBuilder
from functools import cached_property
from io import BytesIO
from tasks.build.common import get_codebuild_artifact_zip_data
from utils.general import logit
from zipfile import ZipFile


class DockerBuilder(Builder):
    def __init__(self, app_config, aws_client_factory, credentials, project_id, block_name, user_dockerfile):
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.credentials = credentials
        self.project_id = project_id
        self.block_name = block_name
        self.user_dockerfile = user_dockerfile

        self.registry_uri = ''

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
    def ecr(self):
        return self.aws_client_factory.get_aws_client(
            "ecr",
            self.credentials
        )

    @cached_property
    def repository_name(self):
        return f'{self.project_id}_{self.block_name}'

    @cached_property
    def s3_key(self):
        return f'buildspecs/{self.repository_name}.zip'

    @cached_property
    def s3_path(self):
        return f"{self.credentials['lambda_packages_bucket']}/{self.s3_key}"

    @cached_property
    def s3_bucket(self):
        return self.credentials['lambda_packages_bucket']

    @cached_property
    def final_s3_package_zip_path(self):
        return f"{self.repository_name}.zip"

    def build(self, rebuild=False):
        docker_env_builder = DockerEnvBuilder(
            self.app_config,
            self.project_id,
            self.user_dockerfile
        )
        zipfile = docker_env_builder.build()

        repository_uri = self.find_repository()
        if repository_uri is None:
            repository_uri = self.create_repository()

        output_zipfile = self.perform_codebuild(zipfile, repository_uri)

        print(output_zipfile)

    def find_repository(self):
        results = self.ecr.describe_repositories(
            repositoryNames=[
                self.repository_name
            ]
        )
        repositories = [repo['repositoryUri'] for repo in results['repositories']]
        if len(repositories) == 0:
            return None
        return repositories[0]

    def create_repository(self):
        # TODO error check
        resp = self.ecr.create_repository(
            repositoryName=self.repository_name
        )
        return resp['repository']['repositoryUri']

    def perform_codebuild(self, zipfile, repository_uri):
        logit(f'Creating codebuild s3 location override at {self.s3_path}')

        self.s3.put_object(
            Bucket=self.credentials['lambda_packages_bucket'],
            Body=zipfile,
            Key=self.s3_key,
            # Legacy indicates this value must be public read, this assertion
            # should be validated in the future.
            ACL="public-read"
        )
        build_id = self.codebuild.start_build(
            projectName='refinery-docker-builds',
            sourceTypeOverride='s3',
            sourceLocationOverride=self.s3_path,
            environmentVariablesOverride=[
                {
                    'name': 'DOCKER_REPOSITORY_URL',
                    'value': repository_uri,
                    'type': 'PLAINTEXT'
                },
                {
                    'name': 'DOCKER_REGISTRY_URI',
                    'value': self.registry_uri,
                    'type': 'PLAINTEXT'
                }
            ],
        )['build']['id']

        logit(f'Completed codebuild id {build_id}')

        return get_codebuild_artifact_zip_data(
            self.aws_client_factory,
            self.credentials,
            build_id,
            self.final_s3_package_zip_path
        )

    def parse_serverless_output(self, serverless_zipfile):
        # TODO return deployment.json created from project.json and serverless_info
        with ZipFile(BytesIO(serverless_zipfile)) as zipfile:
            with zipfile.open('serverless_info') as serverless_info:
                text = serverless_info.read().decode("UTF-8")
                parser = ServerlessInfoParser(text)

                return parser.lambda_resource_map
