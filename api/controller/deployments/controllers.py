import json
from uuid import uuid4

import pinject
from jsonschema import validate as validate_schema
from tornado import gen

from controller import BaseHandler
from controller.decorators import authenticated
from controller.deployments.schemas import *
from data_types.deployment_stages import DeploymentStages
from deployment.deployment_manager import DeploymentManager
from deployment.serverless.exceptions import RefineryDeploymentException
from deployment.serverless.utils import get_unique_workflow_state_name
from models import Deployment, CachedExecutionLogsShard, Project, DeploymentLog, ProjectVersion
from models.deployment_auth import DeploymentAuth, session_scope
from pyconstants.project_constants import PYTHON_36_TEMPORAL_RUNTIME_PRETTY_NAME, DOCKER_RUNTIME_PRETTY_NAME
from utils.locker import AcquireFailure


class DeploySecureResolverDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, deployment_manager):
        pass


class SecureResolverDeployment(BaseHandler):
    dependencies = DeploySecureResolverDependencies
    deployment_manager: DeploymentManager = None

    def get_project(self, project_id):
        if project_id is not None:
            project = self.dbsession.query(Project).filter_by(
                id=project_id
            ).first()
            if project is None:
                self.write({
                    "success": False,
                    "msg": "unable to find project with given ID"
                })
                raise gen.Return()

            return project_id, project.name

        project_name = "secure-resolver"
        project = self.dbsession.query(Project).filter_by(
            name=project_name
        ).first()

        if project is None:
            project = Project()
            project.name = project_name
            self.dbsession.add(project)
            project.users.append(self.authenticated_user)
            self.dbsession.commit()

        return project.id, project_name

    @gen.coroutine
    def post(self):
        validate_schema(self.json, DEPLOY_SECURE_RESOLVER_SCHEMA)

        project_id = self.json.get("project_id")
        project_id, _ = self.get_project(project_id)

        lock_id = "deploy_diagram_" + project_id

        task_lock = self.task_locker.lock(self.dbsession, lock_id)

        try:
            # Enforce that we are only attempting to do this multiple times simultaneously for the same project
            with task_lock:
                yield self.do_deployment()

        except AcquireFailure:
            self.logger("Unable to acquire deploy diagram lock for " + project_id)
            self.write({
                "success": False,
                "code": "DEPLOYMENT_LOCK_FAILURE",
                "msg": "Deployment for this project is already in progress",
            })

    def get_deployment_url(self, deployment_id):
        # deployment_id is used as a "tag" here since we can't guarantee that it will be unique since
        # the customer is providing it
        deployment = self.deployment_manager.get_deployment_with_tag(self.dbsession, deployment_id)
        if deployment is None:
            self.logger("no latest deployment for project")
            return None

        deployment_json = json.loads(deployment.deployment_json)
        workflow_states = deployment_json["workflow_states"]
        ws_lookup_by_type = {ws["type"]: ws for ws in workflow_states}

        api_endpoint = ws_lookup_by_type["api_endpoint"]
        return api_endpoint["url"]

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

    @gen.coroutine
    def build_secure_resolver(self, credentials, org_id, project_id, project_name, stage):
        container_uri = self.json["container_uri"]
        language = self.json["language"]
        functions = self.json["functions"]

        self.logger(f"Deploying {project_id}")

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

        deployment = self.deployment_manager.get_latest_deployment(self.dbsession, project_id, stage)
        if deployment is not None:
            deployment_json = json.loads(deployment.deployment_json)

            workflow_states = deployment_json["workflow_states"]
            ws_lookup_by_name = {ws["name"] if ws.get("name") else ws.get("api_path"): ws for ws in workflow_states}

            for name, id_ in name_to_id.items():
                set_ws_id(ws_lookup_by_name, name_to_id, name, id_)

        app_dir = self.json["app_dir"]

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

        latest_project_version = self.dbsession.query(ProjectVersion).filter_by(
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

        project = self.dbsession.query(Project).filter_by(
            id=project_id
        ).first()
        project.versions.append(
            new_project_version
        )
        self.dbsession.commit()

        try:
            yield self.deployment_manager.deploy_stage(
                credentials,
                org_id, project_id, stage,
                diagram_data,
                deploy_workflows=False,
                # TODO this should be function_names, not just one function_name
                function_name=None,
                new_deployment_id=deployment_id
            )
        except RefineryDeploymentException as e:
            self.write({
                "success": False,
                "msg": str(e)
            })

    @gen.coroutine
    def do_deployment(self):
        action = self.json["action"]

        secret = self.request.headers.get('REFINERY_DEPLOYMENT_SECRET')
        if secret is None:
            self.write({
                "success": False,
                "msg": "secret not provided"
            })
            raise gen.Return()

        deployment_auth: DeploymentAuth = self.dbsession.query(DeploymentAuth).filter_by(
            secret=secret
        ).first()

        if deployment_auth is None:
            self.write({
                "success": False,
                "msg": "no organization for provided secret"
            })
            raise gen.Return()

        project_id = self.json.get("project_id")
        project_id, project_name = self.get_project(project_id)

        credentials = self.get_authenticated_user_cloud_configuration(org_id=deployment_auth.org_id)

        self.dbsession.close()
        self._dbsession = None

        if action == "url":
            deployment_id = self.json.get("deployment_id")
            url = self.get_deployment_url(deployment_id)
            if url is None:
                self.write({
                    "error": "no api endpoint in deployed project"
                })
                raise gen.Return()

            self.write({
                "url": url
            })

        elif action == "build":
            stage = DeploymentStages(self.json["stage"])
            yield self.build_secure_resolver(
                credentials, deployment_auth.org_id, project_id, project_name, stage)
        elif action == "remove":
            stage = DeploymentStages(self.json["stage"])
            self.logger(f"Removing deployment for {project_id}")
            try:
                yield self.deployment_manager.remove_latest_stage(
                    credentials,
                    project_id, stage,
                    remove_workflows=False,
                )
            except RefineryDeploymentException as e:
                self.write({
                    "success": False,
                    "msg": str(e)
                })
        else:
            self.write({
                "success": False,
                "msg": "action not supported: " + action
            })


class GetLatestProjectDeployment(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Get latest deployment for a given project ID
        """
        validate_schema(self.json, GET_LATEST_PROJECT_DEPLOYMENT_SCHEMA)

        self.logger("Retrieving project deployments...")

        # Ensure user is owner of the project
        if not self.is_owner_of_project(self.json["project_id"]):
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have priveleges to get this project deployment!",
            })
            raise gen.Return()

        latest_deployment = self.dbsession.query(Deployment).filter_by(
            project_id=self.json["project_id"]
        ).order_by(
            Deployment.timestamp.desc()
        ).first()

        result_data = False

        if latest_deployment:
            result_data = latest_deployment.to_dict()

        self.write({
            "success": True,
            "result": result_data
        })


class DeleteDeploymentsInProject(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Delete all deployments in database for a given project
        """
        validate_schema(self.json, DELETE_DEPLOYMENTS_IN_PROJECT_SCHEMA)

        self.logger("Deleting deployments from database...")

        # Ensure user is owner of the project
        if not self.is_owner_of_project(self.json["project_id"]):
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have priveleges to delete that deployment!",
            })
            raise gen.Return()

        deployments = self.dbsession.query(Deployment).filter_by(
            project_id=self.json["project_id"]
        )

        for deployment in deployments:
            self.dbsession.delete(deployment)
            self.dbsession.commit()

        # Delete the cached shards in the database
        self.dbsession.query(
            CachedExecutionLogsShard
        ).filter(
            CachedExecutionLogsShard.project_id == self.json["project_id"]
        ).delete()
        self.dbsession.commit()

        self.write({
            "success": True
        })
