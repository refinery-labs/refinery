from functools import cached_property


class DeploymentConfigBuilder:
    def __init__(self, project_id, diagram_data, lambda_resource_map):
        self.project_id = project_id
        self.diagram_data = diagram_data
        self.lambda_resource_map = lambda_resource_map
        self.deployment = {
            "name": diagram_data['name'],
            "project_id": project_id,
            "global_handlers": {},
            "workflow_relationships": [],
            "workflow_states": []
        }

    @cached_property
    def value(self):
        pass

    def add_workflow_relationship(self):
        pass

    def add_workflow_state(self):
        pass