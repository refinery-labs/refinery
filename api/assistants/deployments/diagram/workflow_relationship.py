from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from assistants.deployments.diagram.errors import InvalidDeployment
from assistants.deployments.diagram.types import RelationshipTypes

if TYPE_CHECKING:
	from assistants.deployments.diagram.workflow_states import WorkflowState


class WorkflowRelationship:
	def __init__(self, _id, _type, origin_node, next_node):
		self.id: str = _id
		self.type: RelationshipTypes = _type
		self.origin_node: WorkflowState = origin_node
		self.next_node: WorkflowState = next_node


class IfWorkflowRelationship(WorkflowRelationship):
	def __init__(self, expression, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.expression = expression


class MergeWorkflowRelationship(WorkflowRelationship):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.merge_states = []

	def set_merge_states(self, merge_states):
		self.merge_states = merge_states
