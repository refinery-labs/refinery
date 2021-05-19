import base64
import io
import json
from uuid import uuid4

import pinject
import tink
from botocore.exceptions import ClientError
from sqlalchemy.orm import scoped_session
from tink import hybrid, cleartext_keyset_handle
from tornado import gen
from typing import Callable

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory
from deployment.deployment_manager import DeploymentManager
from models import ProjectVersion, Project
from pyconstants.project_constants import DOCKER_RUNTIME_PRETTY_NAME
from utils.crypto_utils import generate_public_private_key_pair, generate_random_alphanum_str
from utils.general import LogLevelTypes


class BuildSecureResolver:
    db_session_maker: scoped_session = None
    deployment_manager: DeploymentManager
    logger: Callable[[str, LogLevelTypes], None]
    aws_client_factory: AwsClientFactory = None

    @pinject.copy_args_to_public_fields
    def __init__(self, logger, db_session_maker, deployment_manager, aws_client_factory):
        pass

    def secrets_manager(self, credentials):
        return self.aws_client_factory.get_aws_client(
            "secretsmanager",
            credentials
        )

    def store_secret(self, secrets_manager, name, secret_value):
        try:
            resp = secrets_manager.create_secret(
                Name=name,
                SecretBinary=secret_value
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code != "ResourceExistsException":
                raise e
            resp = secrets_manager.put_secret_value(
                SecretId=name,
                SecretBinary=secret_value
            )
            # fallthrough

        return resp.get('ARN')

    @gen.coroutine
    def build_secure_resolver(self, payload, credentials, org_id, project_id, project_name, stage):
        container_uri = payload["container_uri"]
        language = payload["language"]
        functions = payload["functions"]
        app_dir = payload["app_dir"]

        # TODO this should not be hard coded here, this ideally should be pulled down dynamically inside
        # the secure frame service if that is supported by the openid auth provider
        auth_provider_public_key = "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUFsbjFtVm1vSVJqREdRNHBWY2NzQgo1eUozREZJdFVlOXpMRlU0bmFxc2ZGWUp5d0t5QXNINDh3VUhrQlgwWlJ1cm5FRW9tdHhtajNGOUIrZForVUxGCmUzSm5GcldEak43WE9GeHluM0pmWGp3VmZFZkEyRnhZTEx4Z3daeGZGRnZjV0NoMmpvZEFsUE82NkxCdGVTYkEKcGNsdlNucDc0WkhDU0VyOERGQ3Y3TFU1MGQwb0greGhyTjFoNllMdkxHTGJkRkZacHZ3MWRyQmFWN0tOdk9SOAp0NHFNYmNUZERqNWZXUEJtS1o1YVk0ZTNwS1g4OVNCYzhDdFlmQmNmU003dTRreGRHSXQrbmthMjlTeUtTWUJ4CldMYzRiRk1LT3dXancwZ2UvTGJud3RGRWxRK1J5VG83QVNqK29OSzNDUk9STkFheFkrT3o4cUwwMGN1d3VvM2EKUFFJREFRQUIKLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg=="

        self.logger(f"Deploying {project_id}", "info")

        deployment_id = str(uuid4())

        ciphertext_bucket_name = "ciphertext-bucket"
        secure_frame_backend_name = "secure-frame-backend"
        secure_frame_bucket_name = "secure-frame-bucket"
        secure_frame_api_path = "/frame"
        secure_resolver_name = "secure-resolver"
        secure_resolver_api_path = f"/execute/{deployment_id}"
        tokenizer_name = "tokenizer"
        tokenize_api_path = "/tokenize"
        detokenize_api_path = "/detokenize"
        session_verify_api_path = "/session/verify"
        session_create_api_path = "/session/verify"
        secure_frame_keyset_name = "secure-frame-keyset"
        secure_frame_signing_keys_name = "secure-frame-signing-keys"

        secret_lookup = {
            secure_frame_keyset_name: None,
            secure_frame_signing_keys_name: None
        }

        name_to_id = {
            secure_resolver_name: str(uuid4()),
            secure_frame_api_path: str(uuid4()),
            ciphertext_bucket_name: str(uuid4()),
            secure_frame_backend_name: str(uuid4()),
            secure_frame_bucket_name: str(uuid4()),
            secure_resolver_api_path: str(uuid4()),
            tokenizer_name: str(uuid4()),
            tokenize_api_path: str(uuid4()),
            detokenize_api_path: str(uuid4()),
            session_verify_api_path: str(uuid4()),
            session_create_api_path: str(uuid4())
        }

        def set_ws_id(from_lookup, to_lookup, name, id_):
            ws = from_lookup.get(name)
            if ws is not None:
                to_lookup[name] = ws["id"]
                return
            to_lookup[name] = id_

        dbsession = self.db_session_maker()
        secrets_manager = self.secrets_manager(credentials)

        deployment = self.deployment_manager.get_latest_deployment(dbsession, project_id, stage)
        if deployment is not None:
            deployment_json = json.loads(deployment.deployment_json)

            workflow_states = deployment_json["workflow_states"]
            ws_lookup_by_name = {ws["name"] if ws.get("name") else ws.get("api_path"): ws for ws in workflow_states}

            for name, id_ in name_to_id.items():
                set_ws_id(ws_lookup_by_name, name_to_id, name, id_)

            secrets = deployment_json.get("secrets")
            if secrets is not None:
                for name, secret in secrets.items():
                    secret_lookup[name] = secret

        # set the secret frame secret if not found
        if secret_lookup.get(secure_frame_keyset_name) is not None:
            hybrid.register()

            private_keyset_handle = tink.new_keyset_handle(hybrid.hybrid_key_templates.ECIES_P256_HKDF_HMAC_SHA256_AES128_GCM)

            stream = io.BytesIO()
            writer = tink.BinaryKeysetWriter(stream)

            # TODO we should not be saving secrets like this, we should be using KMS to store this value
            cleartext_keyset_handle.write(writer, private_keyset_handle)

            secret_name = f"{secure_frame_keyset_name}-{project_id}"
            secret_arn = self.store_secret(secrets_manager, secret_name, stream.getvalue())

            secret_lookup[secure_frame_keyset_name] = secret_arn

        if secret_lookup.get(secure_frame_signing_keys_name) is not None:
            secure_frame_public_key, secure_frame_private_key = generate_public_private_key_pair()
            secure_frame_secret = json.dumps({
                "public_key": base64.b64encode(secure_frame_public_key).decode(),
                "private_key": base64.b64encode(secure_frame_private_key).decode(),
            })

            secret_name = f"{secure_frame_signing_keys_name}-{project_id}"
            secret_arn = self.store_secret(secrets_manager, secret_name, secure_frame_secret)

            secret_lookup[secure_frame_signing_keys_name] = secret_arn

        secure_resolver_id = name_to_id[secure_resolver_name]
        secure_resolver = self.create_secure_resolver_workflow_state(
            secure_resolver_id, secure_resolver_name, container_uri, functions, app_dir, language
        )

        secure_frame_backend_id = name_to_id[secure_frame_backend_name]
        secure_frame_backend = self.create_secure_frame_backend(
            secure_frame_backend_id, secure_frame_backend_name,
            secret_lookup[secure_frame_signing_keys_name],
            secret_lookup[secure_frame_keyset_name],
            auth_provider_public_key,
            secure_resolver_id
        )

        ciphertext_bucket_id = name_to_id[ciphertext_bucket_name]
        ciphertext_bucket = self.create_ciphertext_bucket(
            ciphertext_bucket_id, ciphertext_bucket_name
        )

        secure_frame_bucket_id = name_to_id[secure_frame_bucket_name]
        secure_frame_bucket = self.create_secure_frame_bucket(
            secure_frame_bucket_id, secure_frame_bucket_name
        )

        tokenizer_id = name_to_id[tokenizer_name]
        tokenizer = self.create_tokenizer_workflow_state(
            tokenizer_id,
            tokenizer_name,
            secure_resolver_id,
            secret_lookup[secure_frame_signing_keys_name]
        )

        secure_frame_endpoint = {
            "id": name_to_id[secure_frame_api_path],
            "type": "api_endpoint",
            "api_path": secure_frame_api_path,
            "http_method": "GET",
            "lambda_proxy": secure_frame_backend["id"]
        }

        secure_resolver_api_endpoint = {
            "id": name_to_id[secure_resolver_api_path],
            "type": "api_endpoint",
            "api_path": secure_resolver_api_path,
            "http_method": "POST",
            "lambda_proxy": secure_resolver["id"]
        }

        tokenize_api_endpoint = {
            "id": name_to_id[tokenize_api_path],
            "type": "api_endpoint",
            "api_path": tokenize_api_path,
            "http_method": "POST",
            "lambda_proxy": tokenizer["id"]
        }

        detokenize_api_endpoint = {
            "id": name_to_id[detokenize_api_path],
            "type": "api_endpoint",
            "api_path": detokenize_api_path,
            "http_method": "POST",
            "lambda_proxy": tokenizer["id"]
        }

        session_verify_api_endpoint = {
            "id": name_to_id[detokenize_api_path],
            "type": "api_endpoint",
            "api_path": detokenize_api_path,
            "http_method": "POST",
            "lambda_proxy": secure_frame_backend["id"]
        }

        session_create_api_endpoint = {
            "id": name_to_id[detokenize_api_path],
            "type": "api_endpoint",
            "api_path": detokenize_api_path,
            "http_method": "POST",
            "lambda_proxy": secure_frame_backend["id"]
        }

        diagram_data = {
            "name": project_name,
            "secrets": secret_lookup,
            "workflow_states": [
                ciphertext_bucket,
                secure_frame_backend,
                secure_frame_bucket,
                secure_frame_endpoint,
                secure_resolver,
                secure_resolver_api_endpoint,
                tokenizer,
                tokenize_api_endpoint,
                detokenize_api_endpoint,
                session_verify_api_endpoint,
                session_create_api_endpoint
            ],
            "workflow_relationships": [
                {
                    "node": name_to_id[secure_resolver_api_path],
                    "name": "then",
                    "type": "then",
                    "next": secure_resolver_id,
                    "expression": "",
                    "id": str(uuid4()),
                    "version": "1.0.0"
                },
                {
                    "node": name_to_id[tokenize_api_path],
                    "name": "then",
                    "type": "then",
                    "next": tokenizer_id,
                    "expression": "",
                    "id": str(uuid4()),
                    "version": "1.0.0"
                },
                {
                    "node": name_to_id[detokenize_api_path],
                    "name": "then",
                    "type": "then",
                    "next": tokenizer_id,
                    "expression": "",
                    "id": str(uuid4()),
                    "version": "1.0.0"
                },
            ],
        }

        latest_project_version = dbsession.query(ProjectVersion).filter_by(
            project_id=project_id
        ).order_by(ProjectVersion.version.desc()).first()

        if latest_project_version is None:
            project_version = 1
        else:
            project_version = (latest_project_version.version + 1)

        new_project_version = ProjectVersion()
        new_project_version.version = project_version
        new_project_version.project_json = json.dumps(
            diagram_data
        )

        project = dbsession.query(Project).filter_by(
            id=project_id
        ).first()
        project.versions.append(
            new_project_version
        )
        dbsession.commit()
        dbsession.close()

        deploy_result = yield self.deployment_manager.deploy_stage(
            credentials,
            org_id, project_id, stage,
            diagram_data,
            deploy_workflows=False,
            # TODO this should be function_names, not just one function_name
            function_name=None,
            new_deployment_id=deployment_id
        )
        raise gen.Return({
            "deployment_tag": deploy_result["deployment_tag"]
        })

    def tokenizer_env_vars(self, ws_id, jwt_signing_keys=None):
        document_vault_s3_bucket = "cryptovault-loq-" + ws_id
        jwt_private_key_env_var = {"SIGNING_KEYS_ARN": jwt_signing_keys} if jwt_signing_keys else {}
        return {
            "LAMBDA_CALLER": "API_GATEWAY",
            "DOCUMENT_VAULT_S3_BUCKET": document_vault_s3_bucket,
            **jwt_private_key_env_var
        }

    def create_lambda_base(self, id_, name, language, policies=None):
        if policies is None:
            policies = []

        default_lambda_policy = self.default_lambda_policy()

        return {
            "id": id_,
            "name": name,
            "type": "lambda",
            "language": language,
            "code": "",
            "libraries": [],
            "max_execution_name": 60,
            "policies": [
                *policies,
                default_lambda_policy
            ]
        }

    def default_lambda_policy(self):
        return {
            "action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "resource": '*'
        }

    def secure_frame_policies(self):
        tokenizer_policies = self.tokenizer_policies()
        return [
            *tokenizer_policies,
            {
                "action": [
                    "secretsmanager:*",
                ],
                "resource": '*'
            }
        ]

    def create_secure_frame_backend(self, secure_frame_id, secure_frame_name, signing_keys, keyset, auth_provider_public_key, secure_resolver_id):
        tokenizer_env_vars = self.tokenizer_env_vars(secure_resolver_id, jwt_signing_keys=signing_keys)
        policies = self.secure_frame_policies()
        return {
            **self.create_lambda_base(
                secure_frame_id, secure_frame_name, DOCKER_RUNTIME_PRETTY_NAME, policies),
            "container": {
                "uri": "public.ecr.aws/d7v1k2o3/secure-frame-backend"
            },
            "environment_variables": {
                **tokenizer_env_vars,
                # TODO (cthompson) this should not be hardcoded, we should be able to build lunasec-node-monorepo/service/src/browser
                # and then push the static assets to the secure frame bucket we create in this deployment
                "CDN_CONFIG": json.dumps({
                    "host": "d1bxkirkuveaaf.cloudfront.net",
                    "main_script": "main.dc2fde6210856cfb0d6c.js",
                    "main_style": "main.css"
                }),
                "SECURE_FRAME_KEYSET_ARN": keyset,
                "AUTH_PROVIDER_PUBLIC_KEY": auth_provider_public_key,
                "AUTH_CALLBACK_URL": "http://sound:3000",
            }
        }

    def create_ciphertext_bucket(self, ciphertext_bucket_id, ciphertext_bucket_name):
        bucket_name = ciphertext_bucket_name + ciphertext_bucket_id
        return {
            "id": ciphertext_bucket_id,
            "name": ciphertext_bucket_name,
            "type": "bucket",
            "bucket_name": bucket_name,
            "cors": True
        }

    def create_secure_frame_bucket(self, secure_frame_bucket_id, secure_frame_bucket_name):
        bucket_name = secure_frame_bucket_name + secure_frame_bucket_id
        return {
            "id": secure_frame_bucket_id,
            "name": secure_frame_bucket_name,
            "type": "bucket",
            "bucket_name": bucket_name,
            "publish": True
        }

    def create_secure_resolver_workflow_state(
            self, secure_resolver_id, secure_resolver_name, container_uri, functions, app_dir, language
    ):
        tokenizer_env_vars = self.tokenizer_env_vars(secure_resolver_id)
        tokenizer_policies = self.tokenizer_policies()
        return {
            **self.create_lambda_base(
                secure_resolver_id, secure_resolver_name, language, tokenizer_policies),
            "container": {
                "uri": container_uri,
                "functions": functions,
                "app_dir": app_dir
            },
            # TODO how long do we want to wait for this to run?
            "environment_variables": {
                **tokenizer_env_vars
            }
        }

    def tokenizer_policies(self):
        return [{
            "action": [
                "dynamodb:*",
                "s3:*"
            ],
            "resource": '*'
        }]

    def create_tokenizer_workflow_state(self, tokenizer_id, tokenizer_name, secure_resolver_id, jwt_signing_keys):
        tokenizer_env_vars = self.tokenizer_env_vars(secure_resolver_id, jwt_signing_keys)
        tokenizer_policies = self.tokenizer_policies()
        return {
            **self.create_lambda_base(
                tokenizer_id, tokenizer_name, DOCKER_RUNTIME_PRETTY_NAME, tokenizer_policies),
            "container": {
                "uri": "public.ecr.aws/d7v1k2o3/refinery-tokenizer"
            },
            "environment_variables": {
                **tokenizer_env_vars
            },
        }

