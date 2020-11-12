from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from assistants.deployments.aws import api_endpoint

if TYPE_CHECKING:
    from assistants.deployments.aws.aws_deployment import AwsDeployment


class ApiEndpointWorkflowState(api_endpoint.ApiEndpointWorkflowState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._workflow_manager_invoke_url = None

    def setup(self, deploy_diagram: AwsDeployment, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)
        self._workflow_manager_invoke_url = deploy_diagram.get_workflow_manager_invoke_url(self.id)

    def deploy(self, task_spawner, project_id, project_config):
        pass
