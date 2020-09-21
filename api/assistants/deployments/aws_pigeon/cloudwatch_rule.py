from __future__ import annotations

import hashlib
import json

from tornado import gen
from typing import Dict, List, TYPE_CHECKING

from assistants.deployments.aws_pigeon.aws_workflow_state import AwsWorkflowState
from assistants.deployments.aws_pigeon.response_types import CloudwatchRuleTarget
from assistants.deployments.aws_pigeon.types import AwsDeploymentState
from assistants.deployments.diagram.scheduled_action import ScheduledActionWorkflowState

if TYPE_CHECKING:
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


class ScheduleTriggerDeploymentState(AwsDeploymentState):
    def __init__(self, name, state_type, state_hash, arn):
        super().__init__(name, state_type, state_hash, arn)

        self.rules: List[CloudwatchRuleTarget] = []

    def __str__(self):
        return f'Schedule Trigger Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}, rules: {self.rules}'


class ScheduleTriggerWorkflowState(AwsWorkflowState, ScheduledActionWorkflowState):
    def __init__(self, *args):
        super().__init__(*args)

        self.schedule_expression = None
        self.description = None
        self.input_string = None

        self.deployed_state: ScheduleTriggerDeploymentState = self.deployed_state

    def serialize(self):
        serialized_ws = super().serialize()
        return {
            **serialized_ws,
            "schedule_expression": self.schedule_expression,
            "input_string": self.input_string,
            "description": self.description
        }

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)

        if self.deployed_state is None:
            self.deployed_state = ScheduleTriggerDeploymentState(self.name, self.type, self.arn, None)

        self.description = workflow_state_json["description"]

    def get_state_hash(self):
        serialized_state = self.serialize()

        serialized_lambda_values = json.dumps(serialized_state).encode('utf-8')
        return hashlib.sha256(serialized_lambda_values).hexdigest()

    def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
        return None

    @gen.coroutine
    def predeploy(self, task_spawner):
        pass

    def deploy(self, task_spawner, project_id, project_config):
        return None
