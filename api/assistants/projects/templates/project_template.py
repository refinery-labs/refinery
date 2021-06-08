import abc
import base64
import io
import json
from functools import cached_property
from uuid import uuid4

import tink
from tink import hybrid, cleartext_keyset_handle
from typing import TypeVar, Generic, Dict, List

from assistants.aws_clients.aws_secrets_manager import AwsSecretsManager, AwsSecretsManagerFactory
from utils.crypto_utils import generate_public_private_key_pair

T = TypeVar('T')


def filter_private_members(d: Dict) -> List:
    filtered_members = []
    for k, v in d.items():
        if not k.startswith("_"):
            filtered_members.append(v)
    return filtered_members


def get_object_members(o):
    return filter_private_members(vars(o))


class ProjectResource:
    def __init__(self, name):
        self.name = name
        self.id = str(uuid4())


class ProjectSecret:
    def __init__(self, name, secret_type):
        self.name = name
        self.secret_type = secret_type
        self.arn = None

    def __str__(self):
        return {
            "name": self.name,
            "arn": self.arn
        }


class ProjectSecrets:
    def __str__(self):
        project_secrets: List[ProjectSecret] = get_object_members(self)
        return {
            secret.name: secret.arn for secret in project_secrets
        }


class ProjectTemplate(abc.ABC, Generic[T]):
    TEMPLATE_RESOURCES = None
    TEMPLATE_SECRETS = None

    def __init__(
        self,
        credentials,
        secrets_manager_factory: AwsSecretsManagerFactory,
        project_id
    ):
        self.credentials = credentials
        self.secrets_manager: AwsSecretsManager = secrets_manager_factory.new_secrets_manager(self.credentials)
        self.project_id = project_id

        assert self.TEMPLATE_RESOURCES is not None
        self.name_to_resource: Dict[str, ProjectResource] = {resource.name: resource for resource in self.template_resources}

        if self.TEMPLATE_SECRETS is not None:
            self.name_to_secret: Dict[str, ProjectSecret] = {secret.name: secret for secret in self.template_secrets}

    def init(self, deployment_json):
        if deployment_json is None:
            return

        self.resolve_known_workflow_state_ids(deployment_json)
        self.resolve_known_secrets(deployment_json)

        self.create_secrets()

    @abc.abstractmethod
    def build(self, inputs: T) -> Dict:
        pass

    @cached_property
    def template_resources(self) -> List[ProjectResource]:
        return get_object_members(self.TEMPLATE_RESOURCES)

    @cached_property
    def template_secrets(self) -> List[ProjectSecret]:
        return get_object_members(self.TEMPLATE_SECRETS)

    def resolve_known_workflow_state_ids(self, deployment_json):
        workflow_states = deployment_json.get("workflow_states")
        if workflow_states is None:
            return

        ws_lookup_by_name = {
            ws["name"] if ws.get("name") else ws.get("api_path"):
                ws for ws in workflow_states
        }

        for name, resource in list(self.name_to_resource.items()):
            ws = ws_lookup_by_name.get(name)
            if ws is None:
                continue
            resource.id = ws["id"]

    def resolve_known_secrets(self, deployment_json):
        secrets = deployment_json.get("secrets")
        if secrets is None:
            return

        for name, secret_arn in secrets.items():
            project_secret = self.name_to_secret.get(name)
            if project_secret is None:
                continue
            project_secret.arn = secret_arn

    def create_secrets(self):
        for project_secret in self.template_secrets:
            # have we already seen this secret in the previous deployment?
            if project_secret.arn is not None:
                continue

            secret_name = f"{project_secret.name}-{self.project_id}"

            if project_secret.secret_type == "hybrid":
                created_secret = self.create_new_hybrid_encryption_keyset()
            elif project_secret.secret_type == "asymmetric":
                created_secret = self.create_new_asymmetric_keypair()
            else:
                raise Exception(f"provided secret type is not supported: {project_secret.secret_type}")

            secret_arn = self.secrets_manager.store_secret(secret_name, created_secret)

            project_secret.arn = secret_arn

    def serialize_secrets(self):
        return [{
            "name": secret.name,
            "arn": secret.arn
        } for secret in get_object_members(self.TEMPLATE_SECRETS)]

    @staticmethod
    def create_new_hybrid_encryption_keyset():
        hybrid.register()

        private_keyset_handle = tink.new_keyset_handle(hybrid.hybrid_key_templates.ECIES_P256_HKDF_HMAC_SHA256_AES128_GCM)

        stream = io.BytesIO()
        writer = tink.BinaryKeysetWriter(stream)

        # TODO we should not be saving secrets like this, we should be using KMS to store this value
        cleartext_keyset_handle.write(writer, private_keyset_handle)

        return stream.getvalue()

    @staticmethod
    def create_new_asymmetric_keypair():
        secure_frame_public_key, secure_frame_private_key = generate_public_private_key_pair()
        return json.dumps({
            "public_key": base64.b64encode(secure_frame_public_key).decode(),
            "private_key": base64.b64encode(secure_frame_private_key).decode(),
        })

    @cached_property
    def default_lambda_policy(self):
        return {
            "action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "resource": '*'
        }

    def create_lambda_base(self, project_resource: ProjectResource, language, policies=None):
        if policies is None:
            policies = []

        return {
            "id": project_resource.id,
            "name": project_resource.name,
            "type": "lambda",
            "language": language,
            "code": "",
            "libraries": [],
            "max_execution_name": 60,
            "policies": [
                *policies,
                self.default_lambda_policy
            ]
        }

    def create_api_endpoint(self, path: ProjectResource, method, lambda_resource: ProjectResource):
        return {
            "id": path.id,
            "type": "api_endpoint",
            "api_path": path.name,
            "http_method": method,
            "lambda_proxy": lambda_resource.id
        }

