from assistants.decorators import aws_exponential_backoff
from botocore.exceptions import ClientError
from data_types.lambda_config import LambdaConfig
from hashlib import sha256
from json import dumps
from resources.base import Resource
from tasks.build.temporal.python import Python36Builder
from tasks.build.temporal.nodejs import NodeJs12Builder
from tasks.s3 import s3_object_exists
from utils.shared_files import (
    add_shared_files_symlink_to_zip, add_shared_files_to_zip
)
from utils.wrapped_aws_functions import lambda_delete_function


BUILDERS = [
    Python36Builder,
    NodeJs12Builder
]
RUNTIME_TO_BUILDER = {b.RUNTIME_PRETTY_NAME: b for b in BUILDERS}


class AWSLambda(Resource):
    _s3_client = None
    _lambda_client = None
    _s3_path = None

    def __init__(self, app_config, aws_client_factory, credentials, lambda_config: LambdaConfig):
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.credentials = credentials
        self.lambda_config = lambda_config

    @property
    def builder(self):
        return RUNTIME_TO_BUILDER[self.lambda_config.runtime]

    @property
    def s3_path(self):
        # Similar to self.uid, but excludes env
        if self._s3_path is None:
            uid_input = bytes("{}{}{}{}".format(
                self.lambda_config.runtime,
                self.lambda_config.code,
                dumps(self.lambda_config.shared_files, sort_keys=True),
                sorted(self.lambda_config.libraries),
            ), encoding='UTF-8')

            self._s3_path = sha256(uid_input).hexdigest() + ".zip"

        return self._s3_path

    @property
    def exists_in_s3(self):
        return s3_object_exists(
            self.aws_client_factory,
            self.credentials,
            self.credentials["lambda_packages_bucket"],
            self.s3_path
        )

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._s3_client = self.aws_client_factory.get_aws_client(
                "s3",
                self.credentials
            )

        return self._s3_client

    @property
    def lambda_client(self):
        if self._lambda_client is None:
            self._lambda_client = self.aws_client_factory.get_aws_client(
                "lambda",
                self.credentials
            )

        return self._lambda_client

    @property
    def uid(self):
        return self.lambda_config.uid

    def deploy(self):
        zip_data = self.get_zip_data()
        self.upload_to_s3(zip_data)

        self.deploy_lambda()

    def get_zip_data(self):
        builder = self.builder(
            self.app_config,
            self.aws_client_factory,
            self.credentials,
            self.code,
            self.libraries
        )
        zip_data = builder.build()

        return self.apply_shared_files(zip_data)

    def upload_to_s3(self, zip_data):
        if self.exists_in_s3:
            return

        # Write it the cache
        self.s3_client.put_object(
            Key=self.path,
            Bucket=self.credentials["lambda_packages_bucket"],
            Body=zip_data,
        )

    def apply_shared_files(self, zip_data):
        if self.lambda_config.is_inline_execution:
            return add_shared_files_symlink_to_zip(zip_data)
        else:
            # If it's an inline execution we don't add the shared files
            # folder because we'll be live injecting them into /tmp/
            # Add shared files to Lambda package as well.
            return add_shared_files_to_zip(zip_data, self.lambda_config.shared_files)

    @aws_exponential_backoff(allowed_errors=["ResourceConflictException"])
    def deploy_lambda(self):
        try:
            return self.create_lambda_function()
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceConflictException":
                # Delete the existing lambda
                lambda_delete_function(self.lambda_client, self.lambda_config.name)

            raise

    def create_lambda_function(self):
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.create_function
        return self.lambda_client.create_function(
            FunctionName=self.lambda_config.name,
            Runtime=self.lambda_config.runtime,
            Role=self.lambda_config.role,
            Handler=self.lambda_config.handler,
            Code={
                "S3Bucket": self.credentials["lambda_packages_bucket"],
                "S3Key": self.s3_path,
            },
            Description=self.lambda_config.description,
            Timeout=self.lambda_config.max_execution_time,
            MemorySize=self.lambda_config.memory,
            Publish=True,
            VpcConfig={},
            Environment={
                "Variables": self.lambda_config.env.copy()
            },
            Tags=self.lambda_config.tags,
            Layers=self.lambda_config.layers
        )

    def teardown(self):
        lambda_delete_function(self.lambda_client, self.lambda_config.name)