import base64
import json
from uuid import uuid4

from botocore.exceptions import ClientError

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory
from config.app_config import AppConfig
from assistants.deployments.base import Builder
from assistants.deployments.serverless.deploy_config_builder import DeploymentConfigBuilder
from assistants.deployments.serverless.exceptions import LambdaInvokeException
from assistants.deployments.serverless.info_parser import ServerlessInfoParser
from assistants.deployments.serverless.module_builder import ServerlessModuleBuilder, ServerlessModuleConfig
from functools import cached_property
from io import BytesIO
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED

from utils.general import logit


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
        self.deployment_tag = None

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
        return f'buildspecs/{self.build_id}.zip'

    @cached_property
    def s3_path(self):
        return f"{self.credentials['lambda_packages_bucket']}/{self.s3_key}"

    @cached_property
    def s3_bucket(self):
        return self.credentials['lambda_packages_bucket']

    @cached_property
    def final_s3_package_zip_path(self):
        return f"{self.build_id}.zip"

    @cached_property
    def serverless_framework_builder_arn(self):
        return self.app_config.get("serverless_framework_builder_arn")

    def build(self, rebuild=False):
        if self.build_id is None:
            logit("Previous build does not exist, creating new build...")
            self.build_id = str(uuid4())

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
        self.deployment_tag = config.deployment_tag

        try:
            serverless_output = self.perform_serverless_deploy(zipfile)
        except LambdaInvokeException as e:
            logit(str(e), "error")
            return None

        logit("Parsing Serverless Framework output...")

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
            error_message = e.response["Error"]["Message"]
            logit(f'Error while accessing previous build artifact ({self.s3_bucket}{self.s3_key}): {error_message}')
            return None

        s3_file_bytes = s3_file["Body"].read()

        return BytesIO(s3_file_bytes)

    def perform_serverless_deploy(self, zipfile):
        logit(f"Creating s3 build bundle override at {self.s3_path}")

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
            "function_name": None,
            "deployment_id": self.deployment_id
        }

        logit(f"Performing Serverless Framework deploy for deployment: {self.deployment_id}...")

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
