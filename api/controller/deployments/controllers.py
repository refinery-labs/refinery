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
from models import Deployment, CachedExecutionLogsShard, Project, DeploymentLog
from models.deployment_auth import DeploymentAuth
from utils.locker import AcquireFailure


class DeploySecureResolverDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, deployment_manager):
        pass


class SecureResolverDeployment(BaseHandler):
    dependencies = DeploySecureResolverDependencies
    deployment_manager: DeploymentManager = None

    def get_project(self):
        project_id = self.json.get("project_id")
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

        project_id, _ = self.get_project()

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

    def get_deployment_url(self, project_id, stage):
        deployment = self.deployment_manager.get_latest_deployment(self.dbsession, project_id, stage)
        if deployment is None:
            self.logger("no latest deployment for project")
            return None

        deployment_json = json.loads(deployment.deployment_json)
        workflow_states = deployment_json["workflow_states"]
        ws_lookup_by_type = {ws["type"]: ws for ws in workflow_states}

        api_endpoint = ws_lookup_by_type["api_endpoint"]
        return api_endpoint["url"]

    def create_secure_resolver_workflow_state(
        self, secure_resolver_id, project_name, container_uri, functions, app_dir, language
    ):
        document_vault_s3_bucket = "cryptovault-loq-" + secure_resolver_id
        return {
            "id": secure_resolver_id,
            "type": "lambda",
            "name": project_name,
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
                "LAMBDA_CALLER": "API_GATEWAY",
                "DOCUMENT_VAULT_S3_BUCKET": document_vault_s3_bucket,
            },
            "language": language,
            "policies": [
                {
                    "action": [
                        "dynamodb:*",
                        "s3:*"
                    ],
                    "resource": '*'
                }
            ]
        }

    @gen.coroutine
    def build_secure_resolver(self, credentials, org_id, project_id, project_name, stage):
        container_uri = self.json["container_uri"]
        language = self.json["language"]
        functions = self.json["functions"]

        self.logger(f"Deploying {project_id}")

        secure_resolver_id = str(uuid4())
        api_endpoint_id = str(uuid4())
        deployment_id = str(uuid4())
        function_name = None

        deployment = self.deployment_manager.get_latest_deployment(self.dbsession, project_id, stage)
        if deployment is not None:
            deployment_json = json.loads(deployment.deployment_json)

            workflow_states = deployment_json["workflow_states"]
            ws_lookup_by_type = {ws["type"]: ws for ws in workflow_states}

            secure_resolver_ws = ws_lookup_by_type.get("lambda")
            if secure_resolver_ws is not None:
                secure_resolver_id = secure_resolver_ws["id"]
                # function_name = secure_resolver_id

            api_endpoint_ws = ws_lookup_by_type.get("api_endpoint")
            if api_endpoint_ws is not None:
                api_endpoint_id = api_endpoint_ws["id"]

        app_dir = self.json["app_dir"]

        secure_resolver = self.create_secure_resolver_workflow_state(
            secure_resolver_id, project_name, container_uri, functions, app_dir, language
        )

        api_endpoint = {
            "id": api_endpoint_id,
            "type": "api_endpoint",
            "api_path": f"/{deployment_id}",
            "http_method": "POST",
            "lambda_proxy": secure_resolver["id"]
        }

        diagram_data = {
            "name": project_name,
            "workflow_states": [
                secure_resolver,
                api_endpoint
            ],
            "workflow_relationships": [
                {
                    "node": api_endpoint_id,
                    "name": "then",
                    "type": "then",
                    "next": secure_resolver_id,
                    "expression": "",
                    "id": str(uuid4()),
                    "version": "1.0.0"
                },
            ],
        }

        try:
            yield self.deployment_manager.deploy_stage(
                credentials,
                org_id, project_id, stage,
                diagram_data,
                deploy_workflows=False,
                function_name=function_name,
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
        stage = DeploymentStages(self.json["stage"])

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

        project_id, project_name = self.get_project()

        credentials = self.get_authenticated_user_cloud_configuration(org_id=deployment_auth.org_id)

        self.dbsession.close()
        self._dbsession = None

        if action == "url":
            url = self.get_deployment_url(project_id, stage)
            if url is None:
                self.write({
                    "success": False,
                    "msg": "no api endpoint in deployed project"
                })
                raise gen.Return()

            self.write({
                "success": True,
                "url": url
            })

        elif action == "build":
            yield self.build_secure_resolver(
                credentials, deployment_auth.org_id, project_id, project_name, stage)
        elif action == "remove":
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
