import json
from uuid import uuid4

import pinject
from sqlalchemy.orm import scoped_session
from tornado import gen
from typing import Callable

from deployment.deployment_manager import DeploymentManager
from models import ProjectVersion, Project
from pyconstants.project_constants import DOCKER_RUNTIME_PRETTY_NAME
from utils.general import LogLevelTypes


class BuildSecureResolver:
    db_session_maker: scoped_session = None
    deployment_manager: DeploymentManager
    logger: Callable[[str, LogLevelTypes], None]

    @pinject.copy_args_to_public_fields
    def __init__(self, logger, db_session_maker, deployment_manager):
        pass

    @gen.coroutine
    def build_secure_resolver(self, action, credentials, org_id, project_id, project_name, stage):
        container_uri = action["container_uri"]
        language = action["language"]
        functions = action["functions"]
        app_dir = action["app_dir"]

        self.logger(f"Deploying {project_id}", "info")

        deployment_id = str(uuid4())

        secure_resolver_name = f"secure-resolver"
        secure_resolver_api_path = f"/{deployment_id}"
        tokenizer_name = f"tokenizer"
        tokenize_api_path = f"/tokenize"
        detokenize_api_path = f"/detokenize"

        name_to_id = {
            secure_resolver_name: str(uuid4()),
            secure_resolver_api_path: str(uuid4()),
            tokenizer_name: str(uuid4()),
            tokenize_api_path: str(uuid4()),
            detokenize_api_path: str(uuid4())
        }

        def set_ws_id(from_lookup, to_lookup, name, id_):
            ws = from_lookup.get(name)
            if ws is not None:
                to_lookup[name] = ws["id"]
                return
            to_lookup[name] = id_

        dbsession = self.db_session_maker()

        deployment = self.deployment_manager.get_latest_deployment(dbsession, project_id, stage)
        if deployment is not None:
            deployment_json = json.loads(deployment.deployment_json)

            workflow_states = deployment_json["workflow_states"]
            ws_lookup_by_name = {ws["name"] if ws.get("name") else ws.get("api_path"): ws for ws in workflow_states}

            for name, id_ in name_to_id.items():
                set_ws_id(ws_lookup_by_name, name_to_id, name, id_)

        secure_resolver_id = name_to_id[secure_resolver_name]
        secure_resolver = self.create_secure_resolver_workflow_state(
            secure_resolver_id, secure_resolver_name, container_uri, functions, app_dir, language
        )

        tokenizer_id = name_to_id[tokenizer_name]
        tokenizer = self.create_tokenizer_workflow_state(tokenizer_id, tokenizer_name, secure_resolver_id)

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

        diagram_data = {
            "name": project_name,
            "workflow_states": [
                secure_resolver,
                secure_resolver_api_endpoint,
                tokenizer,
                tokenize_api_endpoint,
                detokenize_api_endpoint
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
        raise gen.Return(deploy_result)

    def create_secure_resolver_workflow_state(
            self, secure_resolver_id, secure_resolver_name, container_uri, functions, app_dir, language
    ):
        tokenizer_env_vars = self.tokenizer_env_vars(secure_resolver_id)
        tokenizer_policy = self.tokenizer_policies()
        return {
            "id": secure_resolver_id,
            "type": "lambda",
            "name": secure_resolver_name,
            "code": "",
            "libraries": [],
            "container": {
                "uri": container_uri,
                "functions": functions,
                "app_dir": app_dir
            },
            # TODO how long do we want to wait for this to run?
            "max_execution_time": 60,
            "environment_variables": {
                **tokenizer_env_vars
            },
            "language": language,
            "policies": [
                tokenizer_policy
            ]
        }

    def tokenizer_env_vars(self, ws_id):
        document_vault_s3_bucket = "cryptovault-loq-" + ws_id
        return {
            "LAMBDA_CALLER": "API_GATEWAY",
            "DOCUMENT_VAULT_S3_BUCKET": document_vault_s3_bucket,
        }

    def tokenizer_policies(self):
        return {
            "action": [
                "dynamodb:*",
                "s3:*"
            ],
            "resource": '*'
        }

    def create_tokenizer_workflow_state(self, tokenizer_id, tokenizer_name, secure_resolver_id):
        tokenizer_env_vars = self.tokenizer_env_vars(secure_resolver_id)
        tokenizer_policy = self.tokenizer_policies()
        return {
            "id": tokenizer_id,
            "type": "lambda",
            "name": tokenizer_name,
            "code": "",
            "libraries": [],
            "container": {
                "uri": "public.ecr.aws/d7v1k2o3/refinery-tokenizer"
            },
            # TODO how long do we want to wait for this to run?
            "max_execution_time": 60,
            "environment_variables": {
                **tokenizer_env_vars
            },
            "language": DOCKER_RUNTIME_PRETTY_NAME,
            "policies": [
                tokenizer_policy
            ]
        }

