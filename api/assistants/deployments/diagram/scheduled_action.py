from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from assistants.deployments.diagram.trigger_state import TriggerWorkflowState

if TYPE_CHECKING:
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


class ScheduledActionWorkflowState(TriggerWorkflowState):
    def __init__(self, *args):
        super().__init__(*args)

        self.schedule_expression = None
        self.input_string = None

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        self.schedule_expression = workflow_state_json["schedule_expression"]
        self.input_string = workflow_state_json["input_string"]
