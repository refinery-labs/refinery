import json
from uuid import uuid4

import pinject
from sqlalchemy.orm import scoped_session
from typing import Callable, Union, Tuple

from assistants.aws_clients.aws_secrets_manager import AwsSecretsManagerFactory
from assistants.projects.exceptions import UnknownProjectIdException, ProjectExistsException
from assistants.projects.templates.secure_enclave_template import SecureEnclaveTemplate
from assistants.projects.templates.secure_resolver_template import SecureResolverTemplate, SecureResolverTemplateInputs
from models import ProjectVersion, Project
from utils.general import LogLevelTypes


TEMPLATE_LOOKUP = {
    "secure-enclave": {
        "template_class": SecureEnclaveTemplate,
        "inputs_class": None
    },
    "secure-resolver": {
        "template_class": SecureResolverTemplate,
        "inputs_class": SecureResolverTemplateInputs
    }
}

TEMPLATE_INPUTS_LOOKUP = {
    "secure-enclave": None,
    "secure-resolver": SecureResolverTemplateInputs
}


class ProjectManager:
    db_session_maker: scoped_session = None
    logger: Callable[[str, LogLevelTypes], None]
    aws_secrets_manager_factory: AwsSecretsManagerFactory = None

    @pinject.copy_args_to_public_fields
    def __init__(self, logger, db_session_maker, aws_secrets_manager_factory):
        pass

    def build_project_from_template(
        self,
        credentials,
        template_name,
        project_id,
        latest_deployment_json,
        template_inputs
    ):
        project_template_config = TEMPLATE_LOOKUP[template_name]

        project_template_class = project_template_config["template_class"]
        project_template_inputs_class = project_template_config["inputs_class"]

        project_template = project_template_class(
            credentials, self.aws_secrets_manager_factory, project_id)

        project_template.init(latest_deployment_json)

        project_template_inputs = None
        if project_template_inputs_class is not None:
            project_template_inputs = project_template_inputs_class(*template_inputs)

        diagram_data = {
            "name": template_name,
            **project_template.build(project_template_inputs)
        }

        return diagram_data

    def create_project(self, dbsession, authenticated_user, project_name) -> Tuple[str, bool]:
        project = dbsession.query(Project).filter_by(
            name=project_name
        ).first()

        if project is not None:
            self.logger(f"Project with the name: {project_name} already exists")
            return project.id, False

        project = Project()
        project.name = project_name
        dbsession.add(project)
        project.users.append(authenticated_user)
        dbsession.commit()

        return project.id, True

    def verify_project(self, dbsession, authenticated_user, project_id):
        project = dbsession.query(Project).filter_by(
            id=project_id
        ).first()

        return project is not None and any([user.id == authenticated_user.id for user in project.users])

    def get_project(self, dbsession, project_id):
        return dbsession.query(Project).filter_by(
            id=project_id
        ).first()

    def remove_project(self, dbsession, project_id):
        project_versions = dbsession.query(ProjectVersion).filter_by(
            project_id=project_id
        ).all()

        for project_version in project_versions:
            dbsession.remove(project_version)

        project = dbsession.query(Project).filter_by(
            id=project_id
        ).first()

        dbsession.remove(project)
        dbsession.commit()

    def get_project_version(self, dbsession, project_id, version=None):
        query_filters = {
            "project_id": project_id
        }
        if version is not None:
            query_filters["version"] = version

        # either get the version specified or the latest version
        project_version = dbsession.query(ProjectVersion).filter_by(
            **query_filters
        ).order_by(
            ProjectVersion.timestamp.desc()
        ).first()

        if project_version is None:
            return None
        return json.loads(project_version.project_json)

    @staticmethod
    def create_new_project_version(dbsession, project_id, diagram_data):
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

        return project_version
