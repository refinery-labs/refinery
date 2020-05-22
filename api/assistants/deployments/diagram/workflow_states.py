from __future__ import annotations

from tornado import gen
from typing import Dict, List, TYPE_CHECKING, Union

from assistants.deployments.diagram.types import StateTypes, RelationshipTypes, DeploymentState
from assistants.deployments.diagram.workflow_relationship import WorkflowRelationship, IfWorkflowRelationship, \
	MergeWorkflowRelationship
from utils.general import get_safe_workflow_state_name

if TYPE_CHECKING:
	from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram

INTERNAL_ERROR_MSG = 'When deploying this project, Refinery experienced an internal error.\nPlease reach out to the Refinery devs if this problem persists.'


class DeploymentException(Exception):
	def __init__(self, node_id, name, node_type, internal_error, msg):
		self.id = node_id
		self.name = name
		self.node_type = node_type
		self.internal_error = internal_error
		self.msg = msg

	def __str__(self):
		return f'name: {self.name}, id: {self.id}, type: {self.node_type}, exception:\n{self.msg}'

	def serialize(self):
		msg = self.msg if not self.internal_error else INTERNAL_ERROR_MSG
		return {
			'name': self.name,
			'id': self.id,
			'type': self.node_type,
			'exception': msg
		}


class WorkflowState(DeploymentState):
	def __init__(self, credentials, _id, name, _type, arn=None, force_redeploy=False):
		super(DeploymentState, self).__init__()

		self._credentials = credentials

		self.id: str = _id
		self.name: str = get_safe_workflow_state_name(name + _id)
		self.type: StateTypes = _type

		self.transitions: Dict[RelationshipTypes, List[WorkflowRelationship]] = {transition_type: [] for
																			   transition_type in RelationshipTypes}

		self.deployed_state: Union[DeploymentState, None] = None

		arn = self.get_arn_name() if arn is None else arn
		self.current_state: DeploymentState = DeploymentState(arn)

		self.force_redeploy = force_redeploy

	@property
	def arn(self):
		return self.current_state.arn if self.state_has_changed() else self.deployed_state.arn

	def set_arn(self, arn):
		self.current_state.arn = arn

	def serialize(self):
		return {
			"id": self.id,
			"name": self.name,
			"type": self.type.value,
			"arn": self.arn,
			"transitions": {
				transition_type.value: [t.serialize() for t in transitions_for_type]
				for transition_type, transitions_for_type in self.transitions.items()
			}
		}

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		self.deployed_state = deploy_diagram.get_previous_state(self.id)

	@gen.coroutine
	def predeploy(self, task_spawner):
		raise gen.Return()

	def deploy(self, task_spawner, project_id, project_config):
		pass

	@gen.coroutine
	def cleanup(self, task_spawner, deployent):
		pass

	def state_has_changed(self) -> bool:
		assert self.current_state is not None

		if self.force_redeploy:
			return True

		if self.deployed_state is None:
			return True
		return self.deployed_state.state_changed(self.current_state)

	def deployed_state_exists(self) -> bool:
		if self.deployed_state is None:
			return False
		return self.deployed_state.exists

	def set_name(self, name):
		self.name = name
		self.current_state.arn = self.get_arn_name()

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
			assert isinstance(merge_transition, MergeWorkflowRelationship)

			if merge_transition.next_node.id == next_node_id:
				merge_transition.set_merge_lambdas(arn_list)
				break
