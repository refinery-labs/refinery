from __future__ import annotations

from botocore.exceptions import ClientError
from tornado import gen

from assistants.deployments.aws import api_gateway
from assistants.deployments.aws_workflow_manager.api_endpoint import ApiEndpointWorkflowState
from utils.general import logit


class ApiGatewayWorkflowState(api_gateway.ApiGatewayWorkflowState):
    @gen.coroutine
    def create_lambda_api_route(self, task_spawner, api_endpoint: ApiEndpointWorkflowState):
        logit(f"Setting up route {api_endpoint.http_method} {api_endpoint.api_path} for API Endpoint '{api_endpoint.name}'...")

        return_data = yield self.ensure_endpoint_exists_in_api_gateway(task_spawner, api_endpoint)

        current_base_pointer_id = return_data.get("current_base_pointer_id")

        # Create method on base resource
        try:
            method_response = yield task_spawner.create_method(
                self._credentials,
                "HTTP Method",
                self.api_gateway_id,
                current_base_pointer_id,
                api_endpoint.http_method,
                False,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConflictException":
                raise

        # Link the API Gateway to the lambda
        link_response = yield task_spawner.link_api_method_to_workflow(
            self._credentials,
            self.api_gateway_id,
            current_base_pointer_id,
            api_endpoint
        )

