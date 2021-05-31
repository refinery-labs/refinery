import json
import pinject
from sqlalchemy.orm import scoped_session, Session
from tornado import gen
from typing import Dict, Callable

from assistants.projects.exceptions import UnknownProjectIdException
from data_types.deployment_stages import DeploymentStages
from assistants.deployments.deployment_manager import DeploymentManager
from assistants.deployments.serverless.exceptions import RefineryDeploymentException
from models import Project, User
from models.initiate_database import session_scope
from utils.general import LogLevelTypes, logit


class ServerlessDeploymentConfig:
    def __init__(self, project_id: str, project_name: str, org_id: str, credentials: Dict, action: Dict, authenticated_user: User):
        self.authenticated_user = authenticated_user
        self.org_id = org_id
        self.project_id = project_id
        self.project_name = project_name
        self.credentials = credentials
        self.action = action


class ServerlessDeployAssistant:
    build_secure_resolver = None
    db_session_maker: scoped_session = None
    deployment_manager: DeploymentManager = None
    logger: Callable[[str, LogLevelTypes], None]

    @pinject.copy_args_to_public_fields
    def __init__(self, build_secure_resolver, db_session_maker, deployment_manager, logger):
        pass

    @gen.coroutine
    def do_deployment(self, config: ServerlessDeploymentConfig):
        action_type = config.action["type"]

        payload = config.action["payload"]

        if action_type == "url":
            deployment_id = payload["deployment_id"]
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

        if action_type == "workflow_states":
            deployment_id = payload["deployment_id"]
            workflow_states = self.get_workflow_states(deployment_id)
            if workflow_states is None:
                raise gen.Return({
                    "success": False,
                    "msg": "no workflow states in deployed project"
                })

            raise gen.Return({
                "success": True,
                "result": {
                    "workflow_states": workflow_states
                }
            })

        if action_type == "secrets":
            deployment_id = payload["deployment_id"]
            secrets = self.get_deployment_secrets(deployment_id)
            if secrets is None:
                raise gen.Return({
                    "success": False,
                    "msg": "no secrets in deployed project"
                })

            raise gen.Return({
                "success": True,
                "result": {
                    "secrets": secrets
                }
            })

        elif action_type == "build_secure_enclave":
            stage = DeploymentStages(payload["stage"])

            try:
                deployment_tag = yield self.build_secure_resolver.build_secure_enclave(
                    config.credentials, config.org_id, config.project_id, config.project_name, stage)

            except RefineryDeploymentException as e:
                raise gen.Return({
                    "success": False,
                    "msg": str(e)
                })
            raise gen.Return({
                "success": True,
                "deployment_tag": deployment_tag
            })

        elif action_type == "build_secure_resolver":
            stage = DeploymentStages(payload["stage"])

            try:
                deployment_tag = yield self.build_secure_resolver.build_secure_resolver(
                    payload, config.credentials, config.org_id, config.project_id, config.project_name, stage)

            except RefineryDeploymentException as e:
                raise gen.Return({
                    "success": False,
                    "msg": str(e)
                })
            raise gen.Return({
                "success": True,
                "deployment_tag": deployment_tag
            })

        elif action_type == "remove":
            stage = DeploymentStages(payload["stage"])
            self.logger(f"Removing deployment for {config.project_id}", "info")
            try:
                yield self.deployment_manager.remove_latest_stage(
                    config.credentials,
                    config.project_id, stage,
                    remove_workflows=False,
                )
            except RefineryDeploymentException as e:
                raise gen.Return({
                    "success": False,
                    "msg": str(e)
                })
            raise gen.Return({
                "success": True
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
            api_endpoints = list(
                filter(
                    lambda ws: ws["type"] == "api_endpoint" and "/execute/" in ws["url"],
                    workflow_states
                )
            )
            if len(api_endpoints) != 1:
                logit(f"api endpoints: {api_endpoints}")
                return None

            return api_endpoints[0]["url"]

    def get_workflow_states(self, deployment_id):
        with session_scope(self.db_session_maker) as dbsession:
            # deployment_id is used as a "tag" here since we can't guarantee that it will be unique since
            # the customer is providing it
            deployment = self.deployment_manager.get_deployment_with_tag(dbsession, deployment_id)

            if deployment is None:
                self.logger("no latest deployment for project", "info")
                return None

            deployment_json = json.loads(deployment.deployment_json)
            return deployment_json["workflow_states"]

    def get_deployment_secrets(self, deployment_id):
        with session_scope(self.db_session_maker) as dbsession:
            # deployment_id is used as a "tag" here since we can't guarantee that it will be unique since
            # the customer is providing it
            deployment = self.deployment_manager.get_deployment_with_tag(dbsession, deployment_id)

            if deployment is None:
                self.logger("no latest deployment for project", "info")
                return None

            deployment_json = json.loads(deployment.deployment_json)
            return deployment_json["secrets"]

    def get_project(self, dbsession: Session, project_id, authenticated_user, project_name):
        if project_id is not None:
            project = dbsession.query(Project).filter_by(
                id=project_id
            ).first()

            if project is None:
                raise UnknownProjectIdException("Unable to find project with given Id")

            return project_id

        project = dbsession.query(Project).filter_by(
            name=project_name
        ).first()

        if project is None:
            project = Project()
            project.name = project_name
            dbsession.add(project)
            project.users.append(authenticated_user)
            dbsession.commit()

        return project.id
