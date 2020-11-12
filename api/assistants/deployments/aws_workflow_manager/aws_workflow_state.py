from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from assistants.deployments.aws import aws_workflow_state

if TYPE_CHECKING:
    from assistants.deployments.aws_workflow_manager.aws_deployment import AwsDeployment


class AwsWorkflowState(aws_workflow_state.AwsWorkflowState):
    def __init__(self, credentials, _id, name, _type, arn=None, force_redeploy=False):
        super().__init__(credentials, _id, name, _type, arn, force_redeploy)

        self._workflow_manager_invoke_url = None

    def setup(self, deploy_diagram: AwsDeployment, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)

        self._workflow_manager_invoke_url = deploy_diagram.get_workflow_manager_invoke_url(self.id)

