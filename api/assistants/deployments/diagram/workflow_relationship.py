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

	def serialize(self, use_arns=True):
		origin_node_id = self.origin_node.arn if use_arns else self.origin_node.id
		next_node_id = self.next_node.arn if use_arns else self.next_node.id
		serialized_arn = {"arn": origin_node_id} if use_arns else {}
		return {
			**serialized_arn,
			"id": self.id,
			"name": str(self.type.value).lower(),
			"type": self.next_node.type.value,
			"arn": self.next_node.arn,
			"node": origin_node_id,
			"next": next_node_id
		}


class IfWorkflowRelationship(WorkflowRelationship):
	def __init__(self, expression, *args, **kwargs):
		super(IfWorkflowRelationship, self).__init__(*args, **kwargs)
		self.expression = expression

	def serialize(self, use_arns=True):
		base_relationship = super(IfWorkflowRelationship, self).serialize(use_arns=use_arns)
		return {
			**base_relationship,
			"expression": self.expression
		}


class MergeWorkflowRelationship(WorkflowRelationship):
	def __init__(self, *args, **kwargs):
		super(MergeWorkflowRelationship, self).__init__(*args, **kwargs)
		self.merge_lambdas = []

	def serialize(self, use_arns=True):
		base_relationship = super(MergeWorkflowRelationship, self).serialize(use_arns=use_arns)
		return {
			**base_relationship,
			"merge_lambdas": self.merge_lambdas
		}
