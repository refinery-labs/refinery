import json
import os

from models.project_config import ProjectConfig
from models.project_versions import ProjectVersion
from models.projects import Project


class ProjectInventoryService:

    DEFAULT_PROJECT_CONFIG = {
        "version": "1.0.0",
        "environment_variables": {},
        "api_gateway": {
            "gateway_id": False,
        },
        "logging": {
            "level": "LOG_ALL",
        }
    }

    def __init__(self, logger):
        self.logger = logger
        self.default_project_directory = "./default_projects/"
        self.default_projects = []

    def read_example_projects_from_disk(self):

        for filename in os.listdir(self.default_project_directory):
            with open(self.default_project_directory + filename, "r") as file_handler:
                self.default_projects.append(
                    json.loads(
                        file_handler.read()
                    )
                )

    def add_example_projects_user(self, user):
        output_projects = []

        # Add default projects to the user's account
        for default_project_data in self.default_projects:
            project_name = default_project_data["name"]

            self.logger("Adding default project name '" + project_name + "' to the user's account...")

            new_project = Project()
            new_project.name = project_name

            # Add the user to the project so they can access it
            new_project.users.append(
                user
            )

            new_project_version = ProjectVersion()
            new_project_version.version = 1
            new_project_version.project_json = json.dumps(
                default_project_data
            )

            # Add new version to the project
            new_project.versions.append(
                new_project_version
            )

            new_project_config = ProjectConfig()
            new_project_config.project_id = new_project.id
            new_project_config.config_json = json.dumps(
                self.DEFAULT_PROJECT_CONFIG
            )

            # Add project config to the new project
            new_project.configs.append(
                new_project_config
            )

            output_projects.append(new_project)

        return output_projects
