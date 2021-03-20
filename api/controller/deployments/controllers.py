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

    @gen.coroutine
    def post(self):
        validate_schema(self.json, DEPLOY_SECURE_RESOLVER_SCHEMA)

        project_id = self.json["project_id"]
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

    @gen.coroutine
    def do_deployment(self):
        action = self.json["action"]
        stage = DeploymentStages(self.json["stage"])
        project_id = self.json["project_id"]
        container_uri = self.json["container_uri"]
        language = self.json["language"]
        functions = self.json["functions"]
        app_dir = self.json["app_dir"]

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

        project = self.dbsession.query(Project).filter_by(
            id=project_id
        ).first()
        if project is None:
            self.write({
                "success": False,
                "msg": "unable to find project with given ID"
            })
            raise gen.Return()

        project_name = project.name

        credentials = self.get_authenticated_user_cloud_configuration(org_id=deployment_auth.org_id)

        self.dbsession.close()
        self._dbsession = None

        if action == "arn":
            deployment = self.deployment_manager.get_latest_deployment(self.dbsession, project_id, stage)
            if deployment is None:
                self.write({
                    "success": False
                })
                raise gen.Return()

            deployment_json = json.loads(deployment.deployment_json)
            workflow_states = deployment_json["workflow_states"]
            arn = workflow_states[0]["arn"]
            self.write({
                "success": True,
                "arn": arn
            })
        elif action == "build":
            self.logger(f"Deploying {project_id}")

            workflow_state_id = str(uuid4())
            function_name = None

            deployment = self.deployment_manager.get_latest_deployment(self.dbsession, project_id, stage)
            if deployment is not None:
                deployment_json = json.loads(deployment.deployment_json)
                workflow_states = deployment_json["workflow_states"]
                workflow_state_id = workflow_states[0]["id"]
                # function_name = workflow_state_id

            workflow_state = {
                "id": workflow_state_id,
                "type": "lambda",
                "code": "",
                "libraries": [],
                "name": project_name,
                "container": {
                    "uri": container_uri,
                    "functions": functions,
                    "app_dir": app_dir
                },
                "language": language,
            }

            diagram_data = {
                "name": project_name,
                "workflow_states": [workflow_state],
                "workflow_relationships": [],
            }

            try:
                yield self.deployment_manager.deploy_stage(
                    credentials,
                    deployment_auth.org_id, project_id, stage,
                    diagram_data,
                    deploy_workflows=False,
                    function_name=function_name
                )
            except RefineryDeploymentException as e:
                self.write({
                    "success": False,
                    "msg": str(e)
                })
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
