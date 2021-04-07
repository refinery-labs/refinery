import pinject
from jsonschema import validate as validate_schema
from tornado import gen

from assistants.deployments.serverless.deploy import ServerlessDeploymentConfig, ServerlessDeployAssistant
from controller import BaseHandler
from controller.decorators import authenticated
from controller.deployments.schemas import *
from deployment.deployment_manager import DeploymentManager
from models import Deployment, CachedExecutionLogsShard
from utils.locker import AcquireFailure


class DeploySecureResolverDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, deployment_manager, serverless_deploy_assistant):
        pass


class SecureResolverDeployment(BaseHandler):
    dependencies = DeploySecureResolverDependencies
    deployment_manager: DeploymentManager = None
    serverless_deploy_assistant: ServerlessDeployAssistant = None


    @gen.coroutine
    def post(self):
        validate_schema(self.json, DEPLOY_SECURE_RESOLVER_SCHEMA)

        project_id = self.json.get("project_id")
        project_id, _ = self.serverless_deploy_assistant.get_project(
            self.dbsession,
            project_id,
            self.authenticated_user
        )

        # TODO: Move this into an auth decorator so it doesn't have to be copy-pasted
        secret = self.request.headers.get('REFINERY_DEPLOYMENT_SECRET')
        if secret is None:
            self.write({
                "success": False,
                "msg": "secret not provided"
            })
            raise gen.Return()

        lock_id = "deploy_diagram_" + project_id

        task_lock = self.task_locker.lock(self.dbsession, lock_id)

        try:
            # Enforce that we are only attempting to do this multiple times simultaneously for the same project
            with task_lock:
                config = ServerlessDeploymentConfig(
                    project_id=project_id,
                    secret=secret,
                    action=self.json["action"],
                    credentials=self.get_authenticated_user_cloud_configuration(),
                    authenticated_user=self.authenticated_user
                )
                result = yield self.dependencies.serverless_deploy_assistant.do_deployment(config)
            self.write(result)

        except AcquireFailure:
            self.logger("Unable to acquire deploy diagram lock for " + project_id)
            self.write({
                "success": False,
                "code": "DEPLOYMENT_LOCK_FAILURE",
                "msg": "Deployment for this project is already in progress",
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
