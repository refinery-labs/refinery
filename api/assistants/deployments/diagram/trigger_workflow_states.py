from __future__ import annotations

from tornado import gen
from typing import Dict, TYPE_CHECKING

from assistants.deployments.diagram.deploy_diagram import InvalidDeployment
from assistants.deployments.diagram.types import StateTypes, SnsTopicDeploymentState, ScheduleTriggerDeploymentState
from assistants.deployments.diagram.workflow_states import WorkflowState
from utils.general import logit

if TYPE_CHECKING:
	from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
	from assistants.task_spawner.task_spawner_assistant import TaskSpawner
	from assistants.deployments.diagram.lambda_workflow_state import LambdaWorkflowState


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

				if future is None:
					continue

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

		self.deployed_state: ScheduleTriggerDeploymentState = self.deployed_state

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		super(ScheduleTriggerWorkflowState, self).setup(deploy_diagram, workflow_state_json)
		if self.deployed_state is None:
			self.deployed_state = ScheduleTriggerDeploymentState(self.type, self.arn, None)

		self.schedule_expression = workflow_state_json["schedule_expression"]
		self.description = workflow_state_json["description"]
		self.input_string = workflow_state_json["input_string"]

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying schedule trigger '{self.name}'...")
		return task_spawner.create_cloudwatch_rule(
			self._credentials,
			self
		)

	@gen.coroutine
	def predeploy(self, task_spawner):
		rule_info = yield task_spawner.get_cloudwatch_rules(
			self._credentials,
			self
		)

		self.deployed_state.exists = rule_info["exists"]
		self.deployed_state.rules = rule_info["rules"]

	def _rule_exists_for_state(self, state: LambdaWorkflowState):
		if not self.deployed_state_exists():
			return False

		return any([rule.arn == state.arn for rule in self.deployed_state.rules])

	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		if self._rule_exists_for_state(next_node):
			# Cloudwatch rule is already configured for this next state
			return None

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
		super(SqsQueueWorkflowState, self).setup(deploy_diagram, workflow_state_json)

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

	@gen.coroutine
	def predeploy(self, task_spawner):
		return task_spawner.get_sqs_existence_info(
			self._credentials,
			self
		)

	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node: LambdaWorkflowState):
		if next_node.deployed_state_exists() and next_node.deployed_state.is_linked_to_trigger(self):
			# We already have this trigger linked to the next node
			return

		return task_spawner.map_sqs_to_lambda(
			self._credentials,
			self,
			next_node,
		)


class SnsTopicWorkflowState(TriggerWorkflowState):
	def __init__(self, *args, **kwargs):
		super(SnsTopicWorkflowState, self).__init__(*args, **kwargs)

		self.deployed_state: SnsTopicDeploymentState = self.deployed_state

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		super(SnsTopicWorkflowState, self).setup(deploy_diagram, workflow_state_json)
		if self.deployed_state is None:
			self.deployed_state = SnsTopicDeploymentState(self.type, self.arn, None)

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying SNS topic '{self.name}'...")

		return task_spawner.create_sns_topic(
			self._credentials,
			self.id,
			self.name
		)

	@gen.coroutine
	def predeploy(self, task_spawner: TaskSpawner):
		sns_subs_info = yield task_spawner.get_sns_topic_subscriptions(
			self._credentials,
			self
		)

		self.deployed_state.exists = sns_subs_info["exists"]
		self.deployed_state.subscriptions = sns_subs_info["subscriptions"]

	@gen.coroutine
	def cleanup(self, task_spawner: TaskSpawner, deployment: DeploymentDiagram):
		for subscription in self.deployed_state.subscriptions:
			sub_arn = subscription.subscription_arn
			endpoint = subscription.endpoint

			exists = deployment.validate_arn_exists(StateTypes.LAMBDA, endpoint)
			if not exists:
				yield task_spawner.unsubscribe_lambda_from_sns_topic(
					self._credentials,
					sub_arn
				)

	def _trigger_exists_for_state(self, state: LambdaWorkflowState):
		if not self.deployed_state_exists():
			return False

		return any([sub.endpoint == state.arn for sub in self.deployed_state.subscriptions])

	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		if self._trigger_exists_for_state(next_node):
			# We already have this trigger connected to this node
			return

		return task_spawner.subscribe_lambda_to_sns_topic(
			self._credentials,
			self,
			next_node,
		)
