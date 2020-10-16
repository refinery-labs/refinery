from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from assistants.deployments.aws_workflow_manager.aws_workflow_state import AwsWorkflowState
from assistants.deployments.diagram.endpoint import EndpointWorkflowState

if TYPE_CHECKING:
    from assistants.deployments.aws.aws_deployment import AwsDeployment

API_GATEWAY_STATE_NAME = "__api_gateway__"
API_GATEWAY_STATE_ARN = "API_GATEWAY"
API_GATEWAY_STAGE_NAME = "refinery"


class ApiEndpointWorkflowState(AwsWorkflowState, EndpointWorkflowState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.rest_api_id = None

    def serialize(self):
        serialized_ws_state = super().serialize()
        return {
            **serialized_ws_state,
            "url": self.url,
            "rest_api_id": self.rest_api_id,
            "http_method": self.http_method,
            "api_path": self.api_path,
            "state_hash": self.current_state.state_hash
        }

    def setup(self, deploy_diagram: AwsDeployment, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)
        self._workflow_manager_invoke_url = deploy_diagram.get_workflow_manager_invoke_url(self.id)

    def set_gateway_id(self, api_gateway_id):
        self.rest_api_id = api_gateway_id

        region = self._credentials["region"]
        api_path = self.api_path
        self.url = f"https://{api_gateway_id}.execute-api.{region}.amazonaws.com/refinery{api_path}"

    def deploy(self, task_spawner, project_id, project_config):
        pass
