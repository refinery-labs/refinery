from __future__ import annotations

from tornado import gen
from typing import Dict, List, TYPE_CHECKING

from assistants.deployments.diagram.workflow_states import WorkflowState

if TYPE_CHECKING:
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
    from assistants.task_spawner.task_spawner_assistant import TaskSpawner


class CodeBlockWorkflowState(WorkflowState):
    def __init__(self, *args, is_inline_execution=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.language = None
        self.code = None
        self.layers = None
        self.libraries = None

        self.is_inline_execution = is_inline_execution

        self.environment_variables = {}
        self.shared_files_list: List = []

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)

        if self.is_inline_execution:
            self.environment_variables = {
                env_var["key"]: env_var["value"]
                for env_var in workflow_state_json["environment_variables"]
            }
        else:
            self.environment_variables = self._get_project_env_vars(deploy_diagram, workflow_state_json)

        if "shared_files" in workflow_state_json:
            self.shared_files_list = workflow_state_json["shared_files"]

        self.shared_files_list.extend(deploy_diagram.lookup_workflow_files(self.id))

        language = workflow_state_json.get("language")
        code = workflow_state_json.get("code")
        libraries = workflow_state_json.get("libraries")
        layers = workflow_state_json.get("layers")

        if language is not None:
            self.language = language

        if code is not None:
            self.code = code

        if libraries is not None:
            self.libraries = libraries

        if layers is not None:
            self.layers = layers

    def serialize(self) -> Dict[str, str]:
        base_ws_state = super().serialize()
        return {
            **base_ws_state,
            "language": self.language,
            "code": self.code,
            "layers": self.layers,
            "libraries": self.libraries,
            "environment_variables": self.environment_variables
        }

    def _get_project_env_vars(self, deploy_diagram: DeploymentDiagram, workflow_state_json):
        workflow_state_env_vars = []

        environment_variables = workflow_state_json.get("environment_variables")

        if environment_variables is None:
            return {}

        tmp_env_vars: Dict[str, Dict[str, str]] = {
            env_var_uuid: env_var
            for env_var_uuid, env_var in environment_variables.items()
        }

        project_env_vars = deploy_diagram.project_config["environment_variables"]
        for env_var_uuid, env_data in tmp_env_vars.items():
            project_env_var = project_env_vars.get(env_var_uuid)

            if project_env_var is None:
                continue

            # Add value to match schema
            tmp_env_vars[env_var_uuid]["value"] = project_env_var["value"]

            workflow_state_env_vars.append({
                "key": tmp_env_vars[env_var_uuid]["name"],
                "value": project_env_var["value"]
            })

        deploy_diagram.set_env_vars_for_workflow_state(self, workflow_state_env_vars)

        return {
            env_var["name"]: env_var.get("value") if env_var.get("value") is not None else ""
            for _, env_var in tmp_env_vars.items()
        }

    @gen.coroutine
    def predeploy(self, task_spawner: TaskSpawner):
        pass

    def deploy(self, task_spawner, project_id, project_config):
        pass

    @gen.coroutine
    def cleanup(self, task_spawner: TaskSpawner, deployment: DeploymentDiagram):
        pass
