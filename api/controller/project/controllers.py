import json

import pinject
from tornado import gen

from assistants.deployments.deployment_manager import DeploymentManager, DeployStageConfig
from assistants.projects.project_manager import ProjectManager
from controller import BaseHandler
from controller.decorators import secret_authentication
from data_types.deployment_stages import DeploymentStages
from utils.locker import AcquireFailure


class ProjectCreateDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, project_manager):
        pass


class ProjectCreateSchema:
    def __init__(self, project_name):
        self.project_name = project_name


class ProjectCreate(BaseHandler):
    dependencies = ProjectCreateDependencies

    project_manager: ProjectManager = None

    @secret_authentication
    @gen.coroutine
    def post(self, user_id):
        user = self.get_authenticated_user(user_id)

        project_create = ProjectCreateSchema(**self.json)

        # TODO (cthompson) catch error project_name already exists
        project_id, new_project = self.project_manager.create_project(
            self.dbsession,
            user,
            project_create.project_name
        )

        self.write({
            "success": True,
            "project_id": project_id,
            "new_project": new_project
        })


class ProjectBuildDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, project_manager, deployment_manager):
        pass


class ProjectBuildSchema:
    def __init__(self, template_name, inputs, stage, project_id):
        self.template_name = template_name
        self.inputs = inputs
        self.stage = stage
        self.project_id = project_id


class ProjectBuild(BaseHandler):
    dependencies = ProjectBuildDependencies

    project_manager: ProjectManager = None
    deployment_manager: DeploymentManager = None

    @secret_authentication
    @gen.coroutine
    def post(self, user_id):
        project_build = ProjectBuildSchema(**self.json)

        user = self.get_authenticated_user(user_id)

        valid_project = self.project_manager.verify_project(
            self.dbsession,
            user,
            project_build.project_id,
        )
        if not valid_project:
            self.write({
                "success": False,
                "error": "project either doesn't exists or user is unauthorized to access project"
            })
            return

        project_id = project_build.project_id

        latest_deployment = self.deployment_manager.get_latest_deployment(
            self.dbsession,
            project_id,
            project_build.stage
        )

        self.logger(f"building project: {project_id} from template: {project_build.template_name}")

        latest_deployment_json = {}
        if latest_deployment and latest_deployment.deployment_json:
            latest_deployment_json = json.loads(latest_deployment.deployment_json)

        credentials = self.get_authenticated_user_cloud_configuration(org_id=user.organization_id)
        diagram_data = self.project_manager.build_project_from_template(
            credentials,
            project_build.template_name,
            project_id,
            latest_deployment_json,
            project_build.inputs
        )

        self.logger(f"creating a new project version for project: {project_id}")

        project_version = self.project_manager.create_new_project_version(
            self.dbsession,
            project_id,
            diagram_data
        )
        self.write({
            "success": True,
            "project_version": project_version
        })


class ProjectDeployDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, project_manager, deployment_manager):
        pass


class ProjectDeploySchema:
    def __init__(self, stage, project_id, project_version=None):
        self.stage = stage
        self.project_id = project_id
        self.project_version = project_version


class ProjectDeploy(BaseHandler):
    dependencies = ProjectDeployDependencies

    project_manager: ProjectManager = None
    deployment_manager: DeploymentManager = None

    @secret_authentication
    @gen.coroutine
    def post(self, user_id):
        user = self.get_authenticated_user(user_id)

        project_deploy = ProjectDeploySchema(**self.json)
        project_id = project_deploy.project_id

        valid_project = self.project_manager.verify_project(
            self.dbsession,
            user,
            project_id,
        )
        if not valid_project:
            self.write({
                "success": False,
                "error": "project either doesn't exists or user is unauthorized to access project"
            })
            return

        project_version_json = self.project_manager.get_project_version(
            self.dbsession, project_id, project_deploy.project_version)

        deployment_stage = DeploymentStages(project_deploy.stage)

        credentials = self.get_authenticated_user_cloud_configuration(org_id=user.organization_id)

        deployment_config: DeployStageConfig = DeployStageConfig(
            credentials,
            user.organization_id,
            project_id,
            deployment_stage,
            project_version_json,
            deploy_workflows=False,
        )

        self.logger(f"starting deployment for project: {project_id} version: {project_deploy.project_version} for stage: {deployment_stage}")

        deployment_id = self.deployment_manager.start_deploy_stage(
            deployment_config
        )

        self.write({
            "success": True,
            "deployment_id": deployment_id
        })


class ProjectDeploymentsDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, project_manager, deployment_manager):
        pass


class ProjectDeploymentsSchema:
    def __init__(self, project_id, stage=None, deployment_tag=None):
        self.project_id = project_id
        self.stage = stage
        self.deployment_tag = deployment_tag


class ProjectDeployments(BaseHandler):
    dependencies = ProjectDeploymentsDependencies

    project_manager: ProjectManager = None
    deployment_manager: DeploymentManager = None

    @secret_authentication
    @gen.coroutine
    def post(self, user_id):
        user = self.get_authenticated_user(user_id)

        project_deployment = ProjectDeploymentsSchema(**self.json)

        project_id = project_deployment.project_id

        valid_project = self.project_manager.verify_project(
            self.dbsession,
            user,
            project_id,
        )
        if not valid_project:
            self.write({
                "success": False,
                "error": "project either doesn't exists or user is unauthorized to access project"
            })
            return

        deployments = self.deployment_manager.query_project_deployments(
            self.dbsession,
            project_id,
            project_deployment.stage,
            project_deployment.deployment_tag,
        )

        serialized_deployments = [
            deployment.to_dict() for deployment in deployments
        ]
        self.write({
            "success": True,
            "deployments": serialized_deployments
        })


class ProjectDeploymentDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, project_manager, deployment_manager):
        pass


class ProjectDeploymentSchema:
    def __init__(self, deployment_id=None, deployment_tag=None):
        self.deployment_id = deployment_id
        self.deployment_tag = deployment_tag


class ProjectDeployment(BaseHandler):
    dependencies = ProjectDeploymentDependencies

    project_manager: ProjectManager = None
    deployment_manager: DeploymentManager = None

    @secret_authentication
    @gen.coroutine
    def post(self, user_id):
        user = self.get_authenticated_user(user_id)

        project_deployment = ProjectDeploymentSchema(**self.json)

        if project_deployment.deployment_id is not None:
            deployment = self.deployment_manager.get_deployment_with_id(
                self.dbsession,
                project_deployment.deployment_id,
            )
        elif project_deployment.deployment_tag is not None:
            deployment = self.deployment_manager.get_deployment_with_tag(
                self.dbsession,
                project_deployment.deployment_tag,
            )
        else:
            self.write({
                "success": False,
                "error": "deployment ID or deployment tag not given"
            })
            return

        valid_project = self.project_manager.verify_project(
            self.dbsession,
            user,
            deployment.project_id
        )
        if not valid_project:
            self.write({
                "success": False,
                "error": "user is unauthorized to access deployment"
            })
            return

        self.write({
            "success": True,
            **deployment.to_dict()
        })


class ProjectRemoveDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, project_manager, deployment_manager):
        pass


class ProjectRemoveSchema:
    def __init__(self, project_id):
        self.project_id = project_id


class ProjectRemove(BaseHandler):
    dependencies = ProjectRemoveDependencies

    project_manager: ProjectManager = None
    deployment_manager: DeploymentManager = None

    @secret_authentication
    @gen.coroutine
    def post(self, user_id):
        user = self.get_authenticated_user(user_id)

        project_remove = ProjectRemoveSchema(**self.json)

        project_id = project_remove.project_id

        valid_project = self.project_manager.verify_project(
            self.dbsession,
            user,
            project_id,
        )
        if not valid_project:
            self.write({
                "success": False,
                "error": "project either doesn't exists or user is unauthorized to access project"
            })
            return

        credentials = self.get_authenticated_user_cloud_configuration(org_id=user.organization_id)

        self.logger(f"removing deployments for project: {project_id}")

        yield self.deployment_manager.remove_project_deployments(
            credentials,
            project_id,
            remove_workflows=False
        )

        self.logger(f"removing saved project: {project_id}")

        self.project_manager.remove_project(self.dbsession, project_id)
