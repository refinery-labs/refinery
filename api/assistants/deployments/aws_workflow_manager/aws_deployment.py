from assistants.deployments.aws import aws_deployment


class AwsDeployment(aws_deployment.AwsDeployment):
    def __init__(self, *args, app_config=None, api_gateway_manager=None, latest_deployment=None, **kwargs):
        super().__init__(*args, app_config=app_config, api_gateway_manager=api_gateway_manager, latest_deployment=latest_deployment, **kwargs)

        self.workflow_manager_api_url = app_config.get("workflow_manager_api_url")

    def get_workflow_manager_invoke_url(self, workflow_state_id: str):
        return f"{self.workflow_manager_api_url}/deployment/{self.deployment_id}/workflow/{workflow_state_id}"

