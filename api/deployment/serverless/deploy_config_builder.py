from copy import copy
from functools import cached_property


class DeploymentConfigBuilder:
    def __init__(self, project_id, diagram_data, lambda_resource_map):
        self.project_id = project_id
        self.diagram_data = diagram_data
        self.lambda_resource_map = lambda_resource_map

    @cached_property
    def value(self):
        relationships = self.get_workflow_relationships()
        states = self.get_workflow_state_mapper(relationships)

        return {
            "name": self.diagram_data['name'],
            "project_id": self.project_id,
            "global_handlers": {},
            "workflow_relationships": relationships,
            "workflow_states": states
        }

    def get_workflow_state_mapper(self, relationships):
        states = []

        for workflow_state in self.diagram_data.get("workflow_states", []):
            uuid = workflow_state['id']
            base = self.get_deployed_workflow_state_base(workflow_state, relationships)

            if uuid in self.lambda_resource_map:
                workflow_state['arn'] = self.lambda_resource_map[uuid]

            states.append(base)

        return states

    def get_deployed_workflow_state_base(self, workflow_state, relationships):
        state = {
            "transitions": {
                "if": [],
                "else": [],
                "exception": [],
                "then": []
            },
            **workflow_state
        }

        self.apply_transitions(state, relationships)

        return state

    def apply_transitions(self, state, relationships):
        node_id = state['id']

        for relationship in relationships:
            rel_node_id = relationship['node']

            if rel_node_id != node_id:
                continue

            type_ = relationship['type']
            next_node_id = relationship['next']
            state['transitions'][type_].append({
                "arn": relationship['arn'],
                "id": relationship['id'],
                "name": relationship['name'],
                'type': relationship['type'],
                'node': self.lambda_resource_map.get(rel_node_id),
                'next': self.lambda_resource_map.get(next_node_id)
            })

    def get_workflow_relationships(self):
        relationships = []

        for rel in self.diagram_data.get("workflow_relationships", []):
            next_node_arn = self.lambda_resource_map.get(rel.get("next"))
            relationship = {**rel}
            relationship['arn'] = next_node_arn

            relationships.append(relationship)

        return relationships
