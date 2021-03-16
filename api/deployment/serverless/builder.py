import base64
import json

from botocore.exceptions import ClientError
from tornado import gen

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory
from config.app_config import AppConfig
from deployment.base import Builder
from deployment.serverless.deploy_config_builder import DeploymentConfigBuilder
from deployment.serverless.exceptions import LambdaInvokeException
from deployment.serverless.info_parser import ServerlessInfoParser
from deployment.serverless.module_builder import ServerlessModuleBuilder, ServerlessModuleConfig
from functools import cached_property
from io import BytesIO
from utils.general import logit
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED


def unzip_file(artifact_zip):
    unpacked_artifact_zip = BytesIO()
    with ZipFile(artifact_zip, 'r', ZIP_STORED) as zipfile, ZipFile(unpacked_artifact_zip, 'w', ZIP_DEFLATED) as new_zipfile:
        for f in zipfile.namelist():
            new_zipfile.writestr(f, zipfile.read(f))
    return unpacked_artifact_zip


class ServerlessBuilder(Builder):
    app_config: AppConfig = None
    aws_client_factory: AwsClientFactory = None
    serverless_module_builder: ServerlessModuleBuilder = None

    def __init__(
        self,
        app_config,
        aws_client_factory,
        serverless_module_builder,
        credentials,
        project_id,
        deployment_id,
        build_id,
        stage,
        diagram_data
    ):
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.serverless_module_builder = serverless_module_builder
        self.credentials = credentials
        self.project_id = project_id
        self.deployment_id = deployment_id
        self.build_id = build_id
        self.stage = stage
        self.diagram_data = diagram_data

    @cached_property
    def lambda_function(self):
        return self.aws_client_factory.get_aws_client(
            "lambda",
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

    @cached_property
    def serverless_framework_builder_arn(self):
        return self.app_config.get("serverless_framework_builder_arn")

    def build(self, rebuild=False):
        artifact_zip = self.get_artifact_zipfile() if rebuild else None

        if artifact_zip is not None:
            artifact_zip = unzip_file(artifact_zip)

        config = ServerlessModuleConfig(
            self.credentials,
            self.project_id,
            self.deployment_id,
            self.stage,
            self.diagram_data
        )

        zipfile = self.serverless_module_builder.build(config, artifact_zip)

        try:
            serverless_output = self.perform_lambda_serverless_deploy(zipfile)
        except LambdaInvokeException as e:
            logit("an error occurred when trying to deploy serverless framework project: " + str(e), "error")
            return None

        parser = ServerlessInfoParser(serverless_output)

        lambda_resource_map = parser.lambda_resource_map

        config_builder = DeploymentConfigBuilder(
            self.credentials,
            self.project_id,
            self.diagram_data,
            self.deployment_id,
            self.build_id,
            lambda_resource_map
        )

        return config_builder.value

    def get_artifact_zipfile(self):
        try:
            s3_file = self.s3.get_object(
                Bucket=self.s3_bucket,
                Key=self.s3_key
            )
        except ClientError as e:
            logit(f'Error while accessing previous build artifact: {e.response}')
            return None

        s3_file_bytes = s3_file["Body"].read()

        return BytesIO(s3_file_bytes)

    def perform_lambda_serverless_deploy(self, zipfile):
        logit(f'Creating s3 build bundle override at {self.s3_path}')

        self.s3.put_object(
            Bucket=self.s3_bucket,
            Body=zipfile,
            Key=self.s3_key,
            # Legacy indicates this value must be public read, this assertion
            # should be validated in the future.
            ACL="public-read"
        )

        payload = {
            "bucket": self.s3_bucket,
            "key": self.s3_key,
            "action": "deploy",
            "stage": self.stage,
            "deployment_id": self.deployment_id
        }

        resp = self.lambda_function.invoke(
            FunctionName=self.serverless_framework_builder_arn,
            InvocationType='RequestResponse',
            LogType='Tail',
            Payload=json.dumps(payload).encode()
        )

        payload = resp["Payload"].read()

        error = resp.get("FunctionError")
        if error is not None:
            log_result = base64.b64decode(resp["LogResult"])
            logit(log_result.decode())
            raise LambdaInvokeException(str(payload))

        decoded_payload = json.loads(payload)

        return decoded_payload.get("output")
