import json

import pinject
from jsonschema import validate as validate_schema
from sqlalchemy import or_ as sql_or, and_, func
from tornado import gen

from assistants.deployments.teardown_manager import AwsTeardownManager
from controller import BaseHandler
from controller.decorators import authenticated
from controller.projects.actions import update_project_config
from controller.projects.schemas import *
from models import Deployment, ProjectVersion, ProjectConfig, Project, ProjectShortLink, User, CachedExecutionLogsShard


class SaveProjectConfig(BaseHandler):
    @authenticated
    def post(self):
        # TODO: The logic for each branch of project exists and project doesn't exist should be refactored
        validate_schema(self.json, SAVE_PROJECT_CONFIG_SCHEMA)

        self.logger("Saving project config to database...")

        project_id = self.json["project_id"]
        project_config = self.json["config"]

        # Deny if they don't have access
        if not self.is_owner_of_project(project_id):
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have the permissions required to save this project config."
            })
            return

        # Update project config
        update_project_config(
            self.dbsession,
            project_id,
            project_config
        )

        self.write({
            "success": True,
            "project_id": project_id,
        })


def serialize_versions(project_versions):
    return [
        {
            "timestamp": project_version.timestamp,
            "version": project_version.version
        }
        for project_version in project_versions
    ]


def serialize_project(project, last_modified, versions, total_versions, deployment_exists):
    return {
        "id": project.id,
        "name": project.name,
        "timestamp": project.timestamp,
        "last_modified": last_modified,
        "deployment": deployment_exists,
        "versions": versions,
        "total_versions": total_versions
    }


class SearchSavedProjects(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Free text search of saved functions, returns matching results.
        """
        validate_schema(self.json, SEARCH_SAVED_PROJECTS_SCHEMA)

        self.logger("Searching saved projects...")

        user_id = self.get_authenticated_user_id()

        query = self.json["query"]

        projects = self.get_projects_by_last_modified(user_id, query)

        results_list = []

        for last_modified, project in projects:
            # Pull all deployments in a batch SQL query
            deployment = self.dbsession.query(Deployment).filter_by(
                project_id=project.id
            ).first()

            deployment_exists = deployment is not None

            project_versions = project.versions.order_by(
                ProjectVersion.timestamp.desc()
            ).limit(10).all()

            versions = serialize_versions(project_versions)

            # Optimized for select speed, per the following posts:
            # https://stackoverflow.com/questions/12941416/how-to-count-rows-with-select-count-with-sqlalchemy
            # https://docs.sqlalchemy.org/en/13/orm/tutorial.html#counting
            total_versions = self.dbsession.query(func.count('*')).select_from(ProjectVersion).filter_by(
                project_id=project.id
            ).scalar()

            project_item = serialize_project(project, last_modified, versions, total_versions, deployment_exists)

            results_list.append(
                project_item
            )

        self.write({
            "success": True,
            "results": results_list
        })

    def get_projects_by_last_modified(self, user_id, query):
        like_query = f"%{query}%"

        t = self.dbsession.query(
            ProjectVersion.project_id,
            func.max(ProjectVersion.timestamp).label('last_modified')
        ).group_by(
            ProjectVersion.project_id
        ).subquery('t')

        projects = self.dbsession.query(
            t.c.last_modified,
            Project
        ).join(
            User, Project.users
        ).filter(
            and_(
                User.id == user_id,
                Project.name.ilike(like_query),
                Project.id == t.c.project_id
            )
        ).order_by(
            t.c.last_modified
        ).all()

        return projects


class GetProjectVersions(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Get project versions for the provided project.
        """
        validate_schema(self.json, GET_PROJECT_VERSIONS_SCHEMA)

        self.logger("Searching saved projects...")

        project_id = self.json["project_id"]

        # Ensure user is owner of the project
        if not self.is_owner_of_project(project_id):
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have privileges to access versions for that project!",
            })
            raise gen.Return()

        project_versions = self.dbsession.query(
            ProjectVersion
        ).filter(
            ProjectVersion.project_id == project_id
        ).order_by(
            ProjectVersion.timestamp.desc()
        ).all()

        versions = serialize_versions(project_versions)

        self.write({
            "success": True,
            "versions": versions
        })


class GetSavedProject(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Get a specific saved project
        """
        schema = {
            "type": "object",
            "properties": {
                    "project_id": {
                        "type": "string",
                    },
                "version": {
                        "type": "integer",
                }
            },
            "required": [
                "project_id"
            ]
        }

        validate_schema(self.json, schema)

        self.logger("Retrieving saved project...")

        # Ensure user is owner of the project
        if not self.is_owner_of_project(self.json["project_id"]):
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have privileges to access that project version!",
            })
            raise gen.Return()

        project = self.fetch_project()

        self.write({
            "success": True,
            "project_id": project.project_id,
            "version": project.version,
            "project_json": project.project_json
        })

    def fetch_project(self):
        if 'version' not in self.json:
            return self.fetch_project_without_version(self.json["project_id"])

        return self.fetch_project_by_version(self.json["project_id"], self.json["version"])

    def fetch_project_by_version(self, id, version):
        project_version_result = self.dbsession.query(ProjectVersion).filter_by(
            project_id=id,
            version=version
        ).first()

        return project_version_result

    def fetch_project_without_version(self, id):
        project_version_result = self.dbsession.query(ProjectVersion).filter_by(
            project_id=id
        ).order_by(ProjectVersion.version.desc()).first()

        return project_version_result


class DeleteSavedProjectDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, aws_teardown_manager):
        pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class DeleteSavedProject(BaseHandler):
    dependencies = DeleteSavedProjectDependencies
    aws_teardown_manager: AwsTeardownManager = None

    @authenticated
    @gen.coroutine
    def post(self):
        """
        Get a specific saved project
        """
        validate_schema(self.json, DELETE_SAVED_PROJECT_SCHEMA)
        project_id = self.json["id"]

        self.logger(f"Deleting saved project {project_id}")

        # Ensure user is owner of the project
        if not self.is_owner_of_project(project_id):
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have privileges to delete that project!",
            })
            raise gen.Return()

        credentials = self.get_authenticated_user_cloud_configuration()

        # Pull the latest project config
        project_config = self.dbsession.query(ProjectConfig).filter_by(
            project_id=project_id
        ).first()

        if project_config is not None:
            yield self.aws_teardown_manager.delete_api_gateway(
                credentials,
                project_config.to_dict()
            )

        # delete all AWS deployments
        deployed_projects = self.dbsession.query(Deployment).filter_by(
            project_id=project_id
        ).all()
        for deployment in deployed_projects:
            # load deployed project workflow states
            deployment_json = json.loads(deployment.deployment_json)

            if "workflow_states" not in deployment_json:
                raise Exception("Corrupt deployment JSON data read from database, missing workflow_states for teardown")

            teardown_nodes = deployment_json["workflow_states"]

            # do the teardown of the deployed aws infra
            yield self.aws_teardown_manager.teardown_infrastructure(
                credentials,
                teardown_nodes
            )

        self.dbsession.query(
            CachedExecutionLogsShard
        ).filter(
            CachedExecutionLogsShard.project_id == project_id
        ).delete()

        # delete existing logs for the project
        self.aws_teardown_manager.delete_logs(
            credentials,
            project_id
        )

        saved_project_result = self.dbsession.query(Project).filter_by(
            id=project_id
        ).first()

        self.dbsession.delete(saved_project_result)
        self.dbsession.commit()

        self.write({
            "success": True
        })


class GetProjectConfig(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Get the project config for a given project ID
        """
        validate_schema(self.json, GET_PROJECT_CONFIG_SCHEMA)

        self.logger("Retrieving project deployments...")

        # Ensure user is owner of the project
        if not self.is_owner_of_project(self.json["project_id"]):
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have privileges to get that project version!",
            })
            raise gen.Return()

        project_config = self.dbsession.query(ProjectConfig).filter_by(
            project_id=self.json["project_id"]
        ).first()

        project_config_data = project_config.to_dict()

        self.write({
            "success": True,
            "result": project_config_data["config_json"]
        })


class SaveProject(BaseHandler):
    @authenticated
    def post(self):
        # TODO:  The logic for each branch of project exists and project doesn't exist should be refactored

        validate_schema(self.json, SAVE_PROJECT_SCHEMA)

        self.logger("Saving project to database...")

        project_id = self.json["project_id"]
        diagram_data = json.loads(self.json["diagram_data"])
        project_name = diagram_data["name"]
        project_version = self.json["version"]
        project_config = self.json["config"]

        # If this is a new project and the name already exists
        # Throw an error to indicate this can't be the case
        if project_id == False:
            for project in self.get_authenticated_user().projects:
                if project.name == project_name:
                    self.write({
                        "success": False,
                        "code": "PROJECT_NAME_EXISTS",
                        "msg": "A project with this name already exists!"
                    })
                    return

        # Check if project already exists
        if project_id:
            previous_project = self.dbsession.query(Project).filter_by(
                id=project_id
            ).first()
        else:
            previous_project = None

        # If a previous project exists, make sure the user has permissions
        # to actually modify it
        if previous_project:
            # Deny if they don't have access
            if not self.is_owner_of_project(project_id):
                self.write({
                    "success": False,
                    "code": "ACCESS_DENIED",
                    "msg": "You do not have the permissions required to save this project."
                })
                return

        # If there is a previous project and the name doesn't match, update it.
        if previous_project and previous_project.name != project_name:
            # Double check that the project name isn't already in use.
            for project in self.get_authenticated_user().projects:
                if project.name == project_name:
                    self.write({
                        "success": False,
                        "code": "PROJECT_NAME_EXISTS",
                        "msg": "Name is already used by another project."
                    })
                    return

            previous_project.name = project_name
            self.dbsession.commit()

        # If there's no previous project, create a new one
        if previous_project is None:
            previous_project = Project()
            previous_project.name = diagram_data["name"]

            # Add the user to the project so they can access it
            previous_project.users.append(
                self.authenticated_user
            )

            self.dbsession.add(previous_project)
            self.dbsession.commit()

            # Set project ID to newly generated ID
            project_id = previous_project.id

        # If project version isn't set we'll update it to be an incremented version
        # from the latest saved version.
        if project_version is False:
            latest_project_version = self.dbsession.query(ProjectVersion).filter_by(
                project_id=project_id
            ).order_by(ProjectVersion.version.desc()).first()

            if latest_project_version is None:
                project_version = 1
            else:
                project_version = (latest_project_version.version + 1)
        else:
            previous_project_version = self.dbsession.query(ProjectVersion).filter_by(
                project_id=project_id,
                version=project_version,
            ).first()

            # Delete previous version with same ID since we're updating it
            if previous_project_version is not None:
                self.dbsession.delete(previous_project_version)
                self.dbsession.commit()

        # Now save new project version
        new_project_version = ProjectVersion()
        new_project_version.version = project_version
        new_project_version.project_json = json.dumps(
            diagram_data
        )

        previous_project.versions.append(
            new_project_version
        )

        # Update project config
        update_project_config(
            self.dbsession,
            project_id,
            project_config
        )

        self.write({
            "success": True,
            "project_id": project_id,
            "project_version": project_version
        })


class RenameProject(BaseHandler):
    @authenticated
    def post(self):
        """
        Rename a project
        """
        validate_schema(self.json, RENAME_PROJECT_SCHEMA)

        project_id = self.json["project_id"]
        project_name = self.json["name"]

        if not self.is_owner_of_project(project_id):
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have the permissions required to save this project."
            })
            return

        # Grab the project from the database by ID
        previous_project = self.dbsession.query(Project).filter_by(
            id=project_id
        ).first()

        # Verify project exists
        if previous_project is None:
            self.write({
                "success": False,
                "code": "ACCESS_DENIED",
                "msg": "You do not have the permissions required to save this project."
            })
            return

        # Check if a project already exists with this name
        for project in self.get_authenticated_user().projects:
            if project.name == project_name:
                self.write({
                    "success": False,
                    "code": "PROJECT_NAME_EXISTS",
                    "msg": "A project with this name already exists!"
                })
                return

        # Grab the latest version of the project
        latest_project_version = self.dbsession.query(ProjectVersion).filter_by(
            project_id=project_id
        ).order_by(ProjectVersion.version.desc()).first()

        # If there is not a latest version of the project, fail out
        if latest_project_version is None:
            self.write({
                "success": False,
                "code": "MISSING_PROJECT",
                "msg": "Unable to locate project data to rename"
            })
            return

        # Generate a new version for the project
        project_version = (latest_project_version.version + 1)

        project_json = json.loads(
            latest_project_version.project_json
        )
        project_json["name"] = project_name

        # Save the updated JSON
        latest_project_version.project_json = json.dumps(project_json)
        latest_project_version.version = project_version

        # Write the name to the project table as well (de-normalized)
        previous_project.name = project_name

        # Save the data to the database
        self.dbsession.commit()

        self.write({
            "success": True,
            "code": "RENAME_SUCCESSFUL",
            "msg": "Project renamed successfully"
        })
        return

