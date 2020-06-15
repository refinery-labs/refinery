from __future__ import annotations

from tornado import gen
from typing import Dict, List, TYPE_CHECKING, Union, TypeVar, Generic

from assistants.deployments.diagram.types import StateTypes, RelationshipTypes, DeploymentState
from assistants.deployments.diagram.workflow_relationship import WorkflowRelationship, IfWorkflowRelationship, \
	MergeWorkflowRelationship
from utils.general import get_safe_workflow_state_name

if TYPE_CHECKING:
	from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
	from assistants.task_spawner.task_spawner_assistant import TaskSpawner


T = TypeVar("T")


class StateLookup(Generic[T]):
	def __init__(self):
		self._state_lookup: Dict[str, T] = {}

	def __getitem__(self, item) -> Union[T, None]:
		return self._state_lookup.get(item)

	def __str__(self):
		return str(self._state_lookup)

	def states(self) -> List[T]:
		return list(self._state_lookup.values())

	def add_state(self, state: T):
		self._state_lookup[state.id] = state

	def get_states_with_type(self, type: StateTypes) -> List[T]:
		return [
			state for state in self._state_lookup.values()
			if state.type == type
		]

	def find_state(self, predicate) -> Union[T, None]:
		return next(iter(self.find_states(predicate)), None)

	def find_states(self, predicate) -> List[T]:
		return [
			state for state in self._state_lookup.values()
			if predicate(state)
		]


class WorkflowState:
	def __init__(self, credentials, _id, name, _type):
		super().__init__()

		self._credentials = credentials

		self.id: str = _id
		self.name: str = get_safe_workflow_state_name(name + _id)
		self.type: StateTypes = _type

		empty_transitions = { transition_type: [] for transition_type in RelationshipTypes }
		self.transitions: Dict[RelationshipTypes, List[WorkflowRelationship]] = empty_transitions

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		return

	def serialize(self):
		return {
			"id": self.id,
			"name": self.name,
			"type": self.type.value
		}

	def get_state_id(self):
		return self.id

	@gen.coroutine
	def predeploy(self, task_spawner: TaskSpawner):
		raise gen.Return()

	def deploy(self, task_spawner: TaskSpawner, project_id, project_config):
		pass

	@gen.coroutine
	def cleanup(self, task_spawner: TaskSpawner, deployment: DeploymentDiagram):
		pass

	def set_merge_siblings_for_target(self, next_node_id, sibling_list):
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
		:param sibling_list: identifiers of sibling blocks
		:return:
		"""
		for merge_transition in self.transitions[RelationshipTypes.MERGE]:
			assert isinstance(merge_transition, MergeWorkflowRelationship)

			if merge_transition.next_node.id == next_node_id:
				merge_transition.set_merge_states(sibling_list)
				break
