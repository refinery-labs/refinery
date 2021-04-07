import json
import pinject
from sqlalchemy.orm import scoped_session, Session
from tornado import gen
from typing import Dict, Callable

from assistants.deployments.serverless.build_secure_resolver import BuildSecureResolver
from assistants.deployments.serverless.exceptions import UnknownProjectIdException
from data_types.deployment_stages import DeploymentStages
from deployment.deployment_manager import DeploymentManager
from deployment.serverless.exceptions import RefineryDeploymentException
from models import Project, User
from models.deployment_auth import DeploymentAuth
from models.initiate_database import session_scope
from utils.general import LogLevelTypes


class ServerlessDeploymentConfig:
    def __init__(self, project_id: str, secret: str, credentials: Dict, action: Dict, authenticated_user: User):
        self.authenticated_user = authenticated_user
        self.project_id = project_id
        self.secret = secret
        self.credentials = credentials
        self.action = action


class ServerlessDeployAssistant:
    build_secure_resolver: BuildSecureResolver = None
    db_session_maker: scoped_session = None
    deployment_manager: DeploymentManager = None
    logger: Callable[[str, LogLevelTypes], None]

    @pinject.copy_args_to_public_fields
    def __init__(self, build_secure_resolver, db_session_maker, deployment_manager, logger):
        pass

    @gen.coroutine
    def do_deployment(self, config: ServerlessDeploymentConfig):
        action_type = config.action["type"]

        dbsession = self.db_session_maker()

        deployment_auth: DeploymentAuth = dbsession.query(DeploymentAuth).filter_by(
            secret=config.secret
        ).first()

        if deployment_auth is None:
            raise gen.Return({
                "success": False,
                "msg": "no organization for provided secret"
            })

        try:
            project_id, project_name = self.get_project(dbsession, config.project_id, config.authenticated_user)
        except UnknownProjectIdException as e:
            raise gen.Return({
                "success": False,
                "msg": str(e)
            })

        dbsession.close()

        if action_type == "url":
            deployment_id = config.action["deployment_id"]
            url = self.get_deployment_url(deployment_id)
            if url is None:
                raise gen.Return({
                    "success": False,
                    "msg": "no api endpoint in deployed project"
                })

            raise gen.Return({
                "success": True,
                "result": {
                    "url": url
                }
            })

        elif action_type == "build":
            stage = DeploymentStages(config.action["stage"])

            try:
                yield self.build_secure_resolver.build_secure_resolver(
                    config.action, config.credentials, deployment_auth.org_id, project_id, project_name, stage)

            except RefineryDeploymentException as e:
                raise gen.Return({
                    "success": False,
                    "msg": str(e)
                })

        elif action_type == "remove":
            stage = DeploymentStages(config.action["stage"])
            self.logger(f"Removing deployment for {project_id}", "info")
            try:
                yield self.deployment_manager.remove_latest_stage(
                    config.credentials,
                    project_id, stage,
                    remove_workflows=False,
                )
            except RefineryDeploymentException as e:
                raise gen.Return({
                    "success": False,
                    "msg": str(e)
                })
        else:
            raise gen.Return({
                "success": False,
                "msg": "action not supported: " + action_type
            })

    def get_deployment_url(self, deployment_id):
        with session_scope(self.db_session_maker) as dbsession:
            # deployment_id is used as a "tag" here since we can't guarantee that it will be unique since
            # the customer is providing it
            deployment = self.deployment_manager.get_deployment_with_tag(dbsession, deployment_id)

            if deployment is None:
                self.logger("no latest deployment for project", "info")
                return None

            deployment_json = json.loads(deployment.deployment_json)
            workflow_states = deployment_json["workflow_states"]
            ws_lookup_by_type = {ws["type"]: ws for ws in workflow_states}

            api_endpoint = ws_lookup_by_type["api_endpoint"]
            return api_endpoint["url"]

    def get_project(self, dbsession: Session, project_id, authenticated_user):

        if project_id is not None:
            project = dbsession.query(Project).filter_by(
                id=project_id
            ).first()

            if project is None:
                raise UnknownProjectIdException("Unable to find project with given Id")

            return project_id, project.name

        project_name = "secure-resolver"
        project = dbsession.query(Project).filter_by(
            name=project_name
        ).first()

        if project is None:
            project = Project()
            project.name = project_name
            dbsession.add(project)
            project.users.append(authenticated_user)
            dbsession.commit()

        return project.id, project_name
