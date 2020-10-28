from assistants.deployments.aws import aws_deployment
from assistants.deployments.aws.new_workflow_object import workflow_relationship_from_json
from assistants.deployments.aws_workflow_manager.api_gateway import ApiGatewayWorkflowState
from assistants.deployments.aws_workflow_manager.new_workflow_object import workflow_state_from_json


class AwsDeployment(aws_deployment.AwsDeployment):
    def __init__(self, *args, app_config=None, api_gateway_manager=None, latest_deployment=None, **kwargs):
        super().__init__(*args, api_gateway_manager=api_gateway_manager, latest_deployment=latest_deployment, **kwargs)

        self.workflow_manager_api_url = app_config.get("workflow_manager_api_url")

    def get_workflow_manager_invoke_url(self, workflow_state_id: str):
        return f"{self.workflow_manager_api_url}/deployment/{self.deployment_id}/workflow/{workflow_state_id}"

    def load_deployment_graph(self, diagram_data):
        # If we have workflow files and links, add them to the deployment
        workflow_files_json = diagram_data.get("workflow_files")
        workflow_file_links_json = diagram_data.get("workflow_file_links")
        if workflow_files_json and workflow_file_links_json:
            self.add_workflow_files(workflow_files_json, workflow_file_links_json)

        # Create an in-memory representation of the deployment data
        for n, workflow_state_json in enumerate(diagram_data["workflow_states"]):
            workflow_state = workflow_state_from_json(
                self.credentials, self, workflow_state_json)

            self.add_workflow_state(workflow_state)

        self.build_transitions(diagram_data)

        # Add transition data to each Lambda
        for workflow_relationship_json in diagram_data["workflow_relationships"]:
            workflow_relationship_from_json(self, workflow_relationship_json)
        self.finalize_merge_transitions()

        # Load all handlers in order to return them back to the front end when
        # serializing.

        self._global_handlers = diagram_data["global_handlers"]

    def _use_or_create_api_gateway(self):
        api_gateway = ApiGatewayWorkflowState(self.credentials)
        api_gateway.setup(self, {})

        self.add_workflow_state(api_gateway)
