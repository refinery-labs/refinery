import pinject
from tornado import gen

from assistants.deployments.deployment_manager import DeploymentManager
from assistants.projects.project_manager import ProjectManager
from assistants.serverless.deploy import ServerlessDeploymentConfig
from controller import BaseHandler
from controller.decorators import secret_authentication
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
        project_create = ProjectCreateSchema(**self.json)

        # TODO (cthompson) catch error project_name already exists
        project_id = self.project_manager.create_project(
            self.dbsession,
            self.authenticated_user,
            project_create.project_name
        )

        self.write({
            "success": True,
            "project_id": project_id
        })


class ProjectBuildDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, project_manager, deployment_manager):
        pass


class ProjectBuildSchema:
    def __init__(self, template_name, inputs, workflow_states, stage, project_id):
        self.template_name = template_name
        self.inputs = inputs
        self.workflow_states = workflow_states
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

        latest_deployment_json = latest_deployment.deployment_json if latest_deployment is not None else {}

        diagram_data = self.project_manager.build_project_from_template(
            self.user_aws_credentials,
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

        lock_id = f"deploy_diagram_{project_id}"

        task_lock = self.task_locker.lock(self.dbsession, lock_id)

        try:
            # Enforce that we are only attempting to do this multiple times simultaneously for the same project
            with task_lock:
                credentials = self.get_authenticated_user_cloud_configuration(org_id=user.organization_id)
                result = self.deployment_manager.deploy_stage(
                    credentials,
                    user.organization_id,
                    project_id,
                    project_deploy.stage,
                    project_version_json,
                    deploy_workflows=False,
                )
                self.write({
                    "success": True,
                    **result
                })

        except AcquireFailure:
            self.logger("Unable to acquire deploy diagram lock for " + project_id)
            self.write({
                "success": False,
                "code": "DEPLOYMENT_LOCK_FAILURE",
                "msg": "Deployment for this project is already in progress",
            })


class ProjectDeploymentDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, project_manager, deployment_manager):
        pass


class ProjectDeploymentSchema:
    def __init__(self, project_id, stage=None, deployment_id=None, deployment_tag=None):
        self.project_id = project_id
        self.stage = stage
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
            project_deployment.deployment_id,
            project_deployment.deployment_tag,
        )
        self.write({
            "success": True,
            "deployments": deployments
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
