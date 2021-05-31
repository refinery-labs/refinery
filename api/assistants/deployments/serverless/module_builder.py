import base64
import json
import os
import tarfile
from uuid import uuid4

import botocore
import pinject

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory
from config.app_config import AppConfig
from assistants.deployments.serverless.config_builder import ServerlessConfigBuilder
from functools import cached_property
from io import BytesIO
from os.path import join

from assistants.deployments.serverless.exceptions import LambdaInvokeException, RefineryDeploymentException
from assistants.deployments.serverless.utils import get_unique_workflow_state_name
from pyconstants.project_constants import PYTHON_36_TEMPORAL_RUNTIME_PRETTY_NAME, LANGUAGE_TO_RUNTIME, \
    CONTAINER_LANGUAGE, LAMBDA_TEMPORAL_RUNTIMES, \
    CONTAINER_RUNTIME_PATH, DOCKER_RUNTIME_PRETTY_NAME
from pyconstants.project_constants import NODEJS_10_TEMPORAL_RUNTIME_PRETTY_NAME
from tasks.build.temporal.nodejs import NodeJsBuilder
from tasks.build.temporal.python import PythonBuilder
from zipfile import ZIP_STORED, ZipFile

from utils.general import add_file_to_zipfile, logit, add_file_to_tar_file

REFINERY_ECR_LIFECYCLE_POLICY = {
    "rules": [
        {
            "rulePriority": 1,
            "description": "Keep only two untagged images, expire all others",
            "selection": {
                "tagStatus": "untagged",
                "countType": "imageCountMoreThan",
                "countNumber": 2
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}


class ServerlessModuleConfig:
    def __init__(self, credentials, project_id, deployment_id, stage, diagram_data):
        self.credentials = credentials
        self.project_id = project_id
        self.deployment_id = deployment_id
        self.stage = stage
        self.diagram_data = diagram_data
        self.deployment_tag = None


class ServerlessModuleBuilder:
    app_config: AppConfig = None
    aws_client_factory: AwsClientFactory = None
    node_js_builder: NodeJsBuilder = None
    python_builder: PythonBuilder = None

    @pinject.copy_args_to_public_fields
    def __init__(self, app_config, aws_client_factory, node_js_builder, python_builder):
        pass

    ###########################################################################
    # High level builder stuff
    ###########################################################################

    def lambda_function(self, credentials):
        return self.aws_client_factory.get_aws_client(
            "lambda",
            credentials
        )

    def ecr(self, credentials):
        return self.aws_client_factory.get_aws_client(
            "ecr",
            credentials
        )

    def s3(self, credentials):
        return self.aws_client_factory.get_aws_client(
            "s3",
            credentials
        )

    @cached_property
    def docker_container_modifier_arn(self):
        return self.app_config.get("docker_container_modifier_arn")

    @cached_property
    def workflow_state_builders(self):
        return {
            "lambda": self.build_lambda,
            "sqs_queue": self.build_sqs_queue
        }

    def build(self, config, buffer=None):
        if buffer is not None:
            self._build(config, buffer)

            return buffer.getvalue()

        with BytesIO() as buffer:
            self._build(config, buffer)
            return buffer.getvalue()

    def _build(self, config, buffer):
        with ZipFile(buffer, 'w', ZIP_STORED) as zipfile:
            self.build_workflow_states(config, zipfile)
            self.build_config(config, zipfile)

    def build_config(self, config: ServerlessModuleConfig, zipfile):
        builder = ServerlessConfigBuilder(
            self.app_config,
            config.credentials,
            config.project_id,
            config.deployment_id,
            config.stage,
            config.diagram_data
        )
        serverless_yaml = builder.build()

        add_file_to_zipfile(zipfile, "serverless.yml", serverless_yaml)

    def build_workflow_states(self, config, zipfile):
        for workflow_state in config.diagram_data['workflow_states']:
            type_ = workflow_state['type']
            builder = self.workflow_state_builders.get(type_)

            if builder:
                builder(config, workflow_state, zipfile)

    ###########################################################################
    # Lambda builder
    ###########################################################################

    @cached_property
    def lambda_builders(self):
        class NoopBuilder:
            @staticmethod
            def build(credentials, code, libraries, file_map):
                pass

        return {
            DOCKER_RUNTIME_PRETTY_NAME: NoopBuilder,
            PYTHON_36_TEMPORAL_RUNTIME_PRETTY_NAME: self.python_builder,
            NODEJS_10_TEMPORAL_RUNTIME_PRETTY_NAME: self.node_js_builder
        }

    def container_runtime_path(self, runtime):
        path = LAMBDA_TEMPORAL_RUNTIMES[CONTAINER_LANGUAGE + runtime]
        return os.path.split(path)[-1]

    def build_lambda(self, config: ServerlessModuleConfig, workflow_state, zipfile):
        id_ = workflow_state['id']
        language = workflow_state['language']
        builder = self.lambda_builders[language]
        code = workflow_state["code"]
        libraries = workflow_state["libraries"]
        container = workflow_state.get('container')
        is_container = container is not None and container != ''

        # TODO this should probably be async so we can speed up deployment
        file_map = {}
        builder.build(config.credentials, code, libraries, file_map)

        if is_container:
            logit(f"Building container: {container} for workflow state: {id_}")
            tag, deployment_tag = self.build_with_container(config, workflow_state, file_map)
            if tag is None:
                raise RefineryDeploymentException(f"unable to get container tag for docker container: {container}")

            logit(f"Container for workflow state: {id_} built with tag: {tag}")

            file_map = {
                "container.json": json.dumps({
                    "tag": tag,
                    "deployment_tag": deployment_tag
                })
            }
            if deployment_tag != "":
                config.deployment_tag = deployment_tag

        for filename, contents in file_map.items():
            add_file_to_zipfile(zipfile, self.get_path(id_, filename), contents)

    def ensure_repository_exists(self, credentials, repo_name):
        try:
            ecr_client = self.ecr(credentials)
            ecr_client.create_repository(
                repositoryName=repo_name
            )
            ecr_client.put_lifecycle_policy(
                repositoryName=repo_name,
                lifecyclePolicyText=json.dumps(REFINERY_ECR_LIFECYCLE_POLICY)
            )
        except botocore.exceptions.ClientError as boto_error:
            if boto_error.response["Error"]["Code"] != "RepositoryAlreadyExistsException":
                # If it's not the exception we expect then throw
                raise RefineryDeploymentException(str(boto_error))

    def ensure_parent_dirs_exist(self, container_tar, added_paths, dir_path):
        path_parts = dir_path.split(os.sep)

        for i, _ in enumerate(path_parts):
            cur_dir = os.path.join(*path_parts[:i+1])
            if cur_dir in added_paths:
                continue

            added_paths.append(cur_dir)

            tarinfo = tarfile.TarInfo(cur_dir)
            tarinfo.type = tarfile.DIRTYPE
            tarinfo.mode = 0o755
            container_tar.addfile(tarinfo)

    def get_container_files(self, buffer, id_, file_map):
        content_root = os.path.join(CONTAINER_RUNTIME_PATH, id_)
        added_paths = []
        with tarfile.open(fileobj=buffer, mode='w') as container_tar:
            for filepath, contents in file_map.items():
                filepath = os.path.join(content_root, filepath)

                dir_path, _ = os.path.split(filepath)
                if dir_path not in added_paths:
                    self.ensure_parent_dirs_exist(container_tar, added_paths, dir_path)

                add_file_to_tar_file(container_tar, filepath, contents)

    def build_with_container(self, config: ServerlessModuleConfig, workflow_state, file_map):
        id_ = workflow_state['id']
        name = workflow_state['name']
        container = workflow_state["container"]
        language = workflow_state['language']
        container_uri = container["uri"]
        functions = container.get("functions")

        # TODO (cthompson) verify the schema of functions

        repo_name = get_unique_workflow_state_name(config.stage, name, id_).lower()

        runtime = LANGUAGE_TO_RUNTIME[language]

        buffer = BytesIO()

        if runtime != "docker":
            self.get_container_files(buffer, id_, file_map)

        container_file_data = buffer.getvalue()

        return self.perform_docker_container_modification(
            config.credentials,
            container_uri,
            repo_name,
            container_file_data,
            runtime,
            functions
        )

    def perform_docker_container_modification(self, credentials, container_uri, repo_name, container_file_data, runtime, functions):
        account_id = credentials["account_id"]
        ecr_registry = f"{account_id}.dkr.ecr.us-west-2.amazonaws.com"
        # S3 object key of the build package, randomly generated.
        s3_key = f"container_files/{str(uuid4())}.tar"

        build_package_bucket = credentials["lambda_packages_bucket"]

        # Write the CodeBuild build package to S3
        s3_client = self.s3(credentials)
        s3_response = s3_client.put_object(
            Bucket=build_package_bucket,
            Body=container_file_data,
            Key=s3_key,
            ACL="public-read"
        )

        # TODO check s3 response

        self.ensure_repository_exists(credentials, repo_name)

        payload = {
            "registry": ecr_registry,
            "base_image": container_uri,
            "new_image_name": repo_name,
            "image_files": {
                "bucket": build_package_bucket,
                "key": s3_key
            },
            "runtime": runtime,
            "functions": functions
        }

        logit("Performing docker container modification: " + json.dumps(payload, indent=2))

        # Invoke docker container modifier lambda
        lambda_client = self.lambda_function(credentials)
        resp = lambda_client.invoke(
            FunctionName=self.docker_container_modifier_arn,
            InvocationType='RequestResponse',
            LogType='Tail',
            Payload=json.dumps(payload).encode()
        )

        error = resp.get("FunctionError")
        if error is not None:
            log_result = base64.b64decode(resp["LogResult"])
            logit(log_result.decode())
            raise LambdaInvokeException(str(payload))

        decoded_payload = json.loads(resp["Payload"].read())

        tag = decoded_payload["tag"]
        deployment_id = decoded_payload["deployment_id"]
        return tag, deployment_id

    def get_path(self, id_, path):
        id_ = ''.join([i for i in id_ if i.isalnum()])

        return join(f'lambda/{id_}', path)

    ###########################################################################
    # SQS builder
    ###########################################################################

    def build_sqs_queue(self, workflow_state, zipfile):
        lambda_fn = self.app_config.get("LAMBDA_TEMPORAL_RUNTIMES")['sqs_notifier']

        add_file_to_zipfile(zipfile, "lambda/queue/index.js", lambda_fn)
