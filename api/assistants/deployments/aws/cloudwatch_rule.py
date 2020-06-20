from __future__ import annotations

import hashlib
import json

from tornado import gen
from typing import Dict, List, TYPE_CHECKING

from assistants.deployments.aws.aws_workflow_state import AwsWorkflowState
from assistants.deployments.aws.lambda_function import LambdaWorkflowState
from assistants.deployments.aws.response_types import CloudwatchRuleTarget
from assistants.deployments.aws.types import AwsDeploymentState
from assistants.deployments.diagram.scheduled_action import ScheduledActionWorkflowState
from utils.general import logit

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

        account_id = self._credentials["account_id"]
        self.events_role_arn = f"arn:aws:iam::{account_id}:role/refinery_default_aws_cloudwatch_role"

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

    def _rule_exists_for_state(self, state: LambdaWorkflowState):
        if not self.deployed_state_exists():
            return False

        return any([rule.arn == state.arn for rule in self.deployed_state.rules])

    def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
        """
        if not self.state_has_changed() and self._rule_exists_for_state(next_node):
            # Cloudwatch rule has not changed and is already configured for this next state
            return None
        """
        return task_spawner.add_rule_target(
            self._credentials,
            self,
            next_node
        )

    @gen.coroutine
    def predeploy(self, task_spawner):
        rule_info = yield task_spawner.get_cloudwatch_rules(
            self._credentials,
            self
        )

        self.deployed_state.exists = rule_info["exists"]
        self.deployed_state.rules = rule_info["rules"]
        self.current_state.state_hash = self.get_state_hash()

    def deploy(self, task_spawner, project_id, project_config):
        if self.deployed_state_exists() and not self.state_has_changed():
            # State for the Cloudwatch rule has not changed
            return None

        logit(f"Deploying schedule trigger '{self.name}'...")
        return task_spawner.create_cloudwatch_rule(
            self._credentials,
            self
        )
