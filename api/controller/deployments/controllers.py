from jsonschema import validate as validate_schema
from tornado import gen

from controller import BaseHandler
from controller.decorators import authenticated
from controller.deployments.schemas import *
from models import Deployment, CachedExecutionLogsShard


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

        deployment = self.dbsession.query(Deployment).filter_by(
            project_id=self.json["project_id"]
        ).first()

        if deployment:
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
