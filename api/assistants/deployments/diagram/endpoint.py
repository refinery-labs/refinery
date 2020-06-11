from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from assistants.deployments.diagram.workflow_states import WorkflowState

if TYPE_CHECKING:
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


class EndpointWorkflowState(WorkflowState):
    def __init__(self, *args):
        super().__init__(*args)

        self.http_method = None
        self.api_path = None
        self.url = None

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        self.http_method = workflow_state_json["http_method"]
        self.api_path = workflow_state_json["api_path"]
