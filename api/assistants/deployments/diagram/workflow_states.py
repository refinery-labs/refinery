from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

from assistants.deployments.diagram.types import StateTypes, RelationshipTypes
from assistants.deployments.diagram.workflow_relationship import WorkflowRelationship, IfWorkflowRelationship, \
	MergeWorkflowRelationship
from utils.general import get_safe_workflow_state_name

if TYPE_CHECKING:
	from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
	from assistants.deployments.diagram.api_endpoint_workflow_states import ApiEndpointWorkflowState
	from assistants.deployments.diagram.lambda_workflow_state import LambdaWorkflowState
	from assistants.deployments.diagram.trigger_workflow_states import SnsTopicWorkflowState, ScheduleTriggerWorkflowState, \
		SqsQueueWorkflowState


class DeploymentException(Exception):
	def __init__(self, node_id, name, node_type, msg):
		self.id = node_id
		self.name = name
		self.node_type = node_type
		self.msg = msg

	def __repr__(self):
		return f'name: {self.name}, id: {self.id}, type: {self.node_type}, exception:\n{self.msg}'


class WorkflowState:
	def __init__(self, credentials, _id, name, _type, arn=None):
		self._credentials = credentials

		self.id: str = _id
		self.name: str = get_safe_workflow_state_name(name)
		self.type: StateTypes = _type
		self.arn = self.get_arn_name() if arn is None else arn

		self.transitions: Dict[RelationshipTypes, List[WorkflowRelationship]] = {transition_type: [] for
																			   transition_type in RelationshipTypes}

	def serialize(self):
		return {
			"id": self.id,
			"name": self.name,
			"type": self.type.value,
			"arn": self.arn
		}

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		pass

	def deploy(self, task_spawner, project_id, project_config):
		pass

	def set_name(self, name):
		self.name = name
		self.arn = self.get_arn_name()

	def get_arn_name(self):
		name_prefix = ''
		if self.type == StateTypes.LAMBDA or self.type == StateTypes.API_ENDPOINT:
			arn_type = 'lambda'
			name_prefix = 'function:'
		elif self.type == StateTypes.SNS_TOPIC:
			arn_type = 'sns'
		elif self.type == StateTypes.SQS_QUEUE:
			arn_type = 'sqs'
		elif self.type == StateTypes.SCHEDULE_TRIGGER:
			arn_type = 'events'
			name_prefix = 'rule/'
		else:
			# For pseudo-nodes like API Responses we don't need to create a teardown entry
			return None

		region = self._credentials["region"]
		account_id = self._credentials["account_id"]

		# Set ARN on workflow state
		return f'arn:aws:{arn_type}:{region}:{account_id}:{name_prefix}{self.name}'

	def create_transition(self, deploy_diagram: DeploymentDiagram, transition_type: RelationshipTypes,
						  next_node: WorkflowState, workflow_relationship_json: Dict):
		if transition_type == RelationshipTypes.IF:
			relationship = IfWorkflowRelationship(
				workflow_relationship_json["expression"],
				workflow_relationship_json["id"],
				transition_type,
				self,
				next_node
			)
		elif transition_type == RelationshipTypes.MERGE:
			relationship = MergeWorkflowRelationship(
				workflow_relationship_json["id"],
				transition_type,
				self,
				next_node
			)
			deploy_diagram.add_node_to_merge_transition(self, next_node)
		else:
			relationship = WorkflowRelationship(
				workflow_relationship_json["id"],
				transition_type,
				self,
				next_node
			)

		self.transitions[transition_type].append(relationship)

	def set_merge_siblings_for_target(self, next_node_id, arn_list):
		"""
		In the case with merge transitions, we need all of the sibilings to
		know of each other, for example take this:

		[a] [b] [c]
		 \  |  /
		  \ | /
		   [d]

		The edges (a, d), (b, d), (c, d) are all merge transitions, we must tell
		a, b, c of each other.

		:param next_node_id: The connected node in the transition (in the example this is 'd')
		:param arn_list: arns of sibling blocks
		:return:
		"""
		for merge_transition in self.transitions[RelationshipTypes.MERGE]:
			if merge_transition.next_node.id == next_node_id:
				merge_transition.merge_lambdas = arn_list
				break
