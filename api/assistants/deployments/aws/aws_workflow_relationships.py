from __future__ import annotations

from typing import TYPE_CHECKING

from assistants.deployments.diagram.workflow_relationship import WorkflowRelationship, IfWorkflowRelationship, \
    MergeWorkflowRelationship

if TYPE_CHECKING:
    from assistants.deployments.aws.aws_workflow_state import AwsWorkflowState


class AwsWorkflowRelationship(WorkflowRelationship):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.origin_node: AwsWorkflowState = self.origin_node
        self.next_node: AwsWorkflowState = self.next_node

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


class AwsIfWorkflowRelationship(IfWorkflowRelationship, AwsWorkflowRelationship):
    def serialize(self, use_arns=True):
        base_relationship = super().serialize(use_arns=use_arns)
        return {
            **base_relationship,
            "expression": self.expression
        }


class AwsMergeWorkflowRelationship(MergeWorkflowRelationship, AwsWorkflowRelationship):
    def serialize(self, use_arns=True):
        base_relationship = super().serialize(use_arns=use_arns)
        return {
            **base_relationship,
            "merge_lambdas": self.merge_states
        }
