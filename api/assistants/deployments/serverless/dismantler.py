from __future__ import annotations

import base64
import json

import pinject

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory
from assistants.deployments.base import Dismantler
from functools import cached_property

from assistants.deployments.serverless.exceptions import LambdaInvokeException
from config.app_config import AppConfig
from utils.general import logit


class ServerlessDismantlerFactory:
    app_config: AppConfig = None
    aws_client_factory: AwsClientFactory = None

    @pinject.copy_args_to_public_fields
    def __init__(self, app_config, aws_client_factory):
        pass

    def new_serverless_dismantler(self, credentials, build_id, stage) -> ServerlessDismantler:
        return ServerlessDismantler(
            self.app_config,
            self.aws_client_factory,
            credentials,
            build_id,
            stage
        )


class ServerlessDismantler(Dismantler):
    def __init__(self, app_config, aws_client_factory, credentials, build_id, stage):
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.credentials = credentials
        self.build_id = build_id
        self.stage = stage

    @cached_property
    def codebuild(self):
        return self.aws_client_factory.get_aws_client(
            "codebuild",
            self.credentials
        )

    @cached_property
    def lambda_function(self):
        return self.aws_client_factory.get_aws_client(
            "lambda",
            self.credentials
        )

    @cached_property
    def s3_key(self):
        return f'buildspecs/{self.build_id}.zip'

    @cached_property
    def s3_bucket(self):
        return self.credentials['lambda_packages_bucket']

    @cached_property
    def s3_path(self):
        return f"{self.s3_bucket}/{self.s3_key}"

    @cached_property
    def serverless_framework_builder_arn(self):
        return self.app_config.get("serverless_framework_builder_arn")

    def dismantle(self):
        payload = {
            "bucket": self.s3_bucket,
            "key": self.s3_key,
            "action": "remove",
            "build_id": self.build_id,
            "stage": self.stage
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

        return json.loads(payload)["output"]
