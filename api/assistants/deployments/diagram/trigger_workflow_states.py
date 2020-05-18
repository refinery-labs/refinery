from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from assistants.deployments.diagram.deploy_diagram import InvalidDeployment
from assistants.deployments.diagram.workflow_states import WorkflowState
from utils.general import logit

if TYPE_CHECKING:
	from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


class WarmerTriggerWorkflowState(WorkflowState):
	pass


class TriggerWorkflowState(WorkflowState):
	# TODO make abstract
	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		return None

	def link_deployed_triggers_to_next_state(self, task_spawner):
		deploy_trigger_futures = []

		for transition_type, transitions in self.transitions.items():
			for transition in transitions:

				future = self._link_trigger_to_next_deployed_state(
					task_spawner, transition.next_node)

				if future is not None:
					deploy_trigger_futures.append(future)

		return deploy_trigger_futures


class ScheduleTriggerWorkflowState(TriggerWorkflowState):
	def __init__(self, *args, **kwargs):
		super(ScheduleTriggerWorkflowState, self).__init__(*args, **kwargs)

		self.schedule_expression = None
		self.description = None
		self.input_string = None

		account_id = self._credentials["account_id"]
		self.events_role_arn = f"arn:aws:iam::{account_id}:role/refinery_default_aws_cloudwatch_role"

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		self.schedule_expression = workflow_state_json["schedule_expression"]
		self.description = workflow_state_json["description"]
		self.input_string = workflow_state_json["input_string"]

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying schedule trigger '{self.name}'...")
		return task_spawner.create_cloudwatch_rule(
			self._credentials,
			self
		)

	def predeploy(self, task_spawner):
		return task_spawner.get_cloudwatch_existence_info(
			self._credentials,
			self
		)

	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		return task_spawner.add_rule_target(
			self._credentials,
			self,
			next_node
		)


class SqsQueueWorkflowState(TriggerWorkflowState):
	def __init__(self, *args, **kwargs):
		super(SqsQueueWorkflowState, self).__init__(*args, **kwargs)

		self.url = ''
		self.batch_size = None
		self.visibility_timeout = 900 # Max Lambda runtime - TODO set this to the linked Lambda amount

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, str]):
		region = self._credentials["region"]
		account_id = self._credentials["account_id"]

		self.url = f"https://sqs.{region}.amazonaws.com/{account_id}/{self.name}"

		try:
			self.batch_size = int(workflow_state_json["batch_size"])
		except ValueError:
			raise InvalidDeployment(f"unable to parse 'batch_size' for SQS Queue: {self.name}")

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying SQS queue '{self.name}'...")
		return task_spawner.create_sqs_queue(
			self._credentials,
			self
		)

	def predeploy(self, task_spawner):
		return task_spawner.get_sqs_existence_info(
			self._credentials,
			self
		)

	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		return task_spawner.map_sqs_to_lambda(
			self._credentials,
			self,
			next_node,
		)


class SnsTopicWorkflowState(TriggerWorkflowState):
	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying SNS topic '{self.name}'...")

		return task_spawner.create_sns_topic(
			self._credentials,
			self.id,
			self.name
		)

	def predeploy(self, task_spawner):
		return task_spawner.get_sns_existence_info(
			self._credentials,
			self
		)

	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		return task_spawner.subscribe_lambda_to_sns_topic(
			self._credentials,
			self,
			next_node,
		)
