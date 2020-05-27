from __future__ import annotations

from tornado import gen
from typing import Dict, TYPE_CHECKING

from assistants.deployments.aws.utils import get_layers_for_lambda
from assistants.deployments.diagram.types import ApiGatewayEndpoint
from assistants.deployments.aws.lambda_function import LambdaWorkflowState
from utils.general import logit

API_GATEWAY_STATE_NAME = "__api_gateway__"
API_GATEWAY_STATE_ARN = "API_GATEWAY"
API_GATEWAY_STAGE_NAME = "refinery"

if TYPE_CHECKING:
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


class ApiEndpointWorkflowState(LambdaWorkflowState):
    def __init__(self, *args, **kwargs):
        super(ApiEndpointWorkflowState, self).__init__(*args, **kwargs)

        self.http_method = None
        self.api_path = None
        self.url = None
        self.rest_api_id = None

        lambda_layers = get_layers_for_lambda("python2.7")

        self.language = "python2.7"
        self.code = ""
        self.libraries = []
        self.max_execution_time = 30
        self.memory = 512
        self.execution_mode = "API_ENDPOINT",
        self.layers = lambda_layers
        self.reserved_concurrency_count = False
        self.is_inline_execution = False
        self.shared_files_list = []

    def serialize(self):
        serialized_ws_state = super().serialize()
        return {
            **serialized_ws_state,
            "url": self.url,
            "rest_api_id": self.rest_api_id,
            "http_method": self.http_method,
            "api_path": self.api_path,
            "state_hash": self.current_state.state_hash
        }

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)

        self.http_method = workflow_state_json["http_method"]
        self.api_path = workflow_state_json["api_path"]

        self.execution_mode = "API_ENDPOINT"

    def set_gateway_id(self, api_gateway_id):
        self.rest_api_id = api_gateway_id

        region = self._credentials["region"]
        api_path = self.api_path
        self.url = f"https://{api_gateway_id}.execute-api.{region}.amazonaws.com/refinery{api_path}"

    def get_lambda_uri(self, api_version):
        region = self._credentials["region"]
        account_id = self._credentials["account_id"]
        return f"arn:aws:apigateway:{region}:lambda:path/{api_version}/functions/arn:aws:lambda:{region}:" + \
               f"{account_id}:function:{self.name}/invocations"

    def get_source_arn(self, rest_api_id: str):
        region = self._credentials["region"]
        account_id = self._credentials["account_id"]

        # For AWS Lambda you need to add a permission to the Lambda function itself
        # via the add_permission API call to allow invocation via the CloudWatch event.
        return f"arn:aws:execute-api:{region}:{account_id}:{rest_api_id}/*/{self.http_method}{self.api_path}"

    @gen.coroutine
    def make_api_path_exist(self, task_spawner, api_gateway: ApiGatewayWorkflowState, path_parts):
        # Set the pointer to the base
        current_base_pointer_id = api_gateway.deployed_state.base_resource_id

        # Path level, continuously updated
        current_path = ""

        # Create entire path from chain
        for path_part in path_parts:
            # Check if there's a conflicting resource here
            current_path += "/" + path_part

            # Get existing resource ID instead of creating one
            api_endpoint = api_gateway.deployed_state.get_endpoint_from_path(current_path)
            if api_endpoint is not None:
                current_base_pointer_id = api_endpoint.id
            else:
                # Otherwise go ahead and create one
                new_resource_id = yield task_spawner.create_resource(
                    self._credentials,
                    api_gateway.api_gateway_id,
                    current_base_pointer_id,
                    path_part
                )
                current_base_pointer_id = new_resource_id

                # Create a new api endpoint resource and add it to our deployed state
                api_endpoint = ApiGatewayEndpoint(current_base_pointer_id, current_path)

                api_gateway.deployed_state.add_endpoint(api_endpoint)

            # The current endpoint we are looking at is in the path of what we are searching for
            # so we will want to prevent it from being cleaned at the end of deployment
            api_endpoint.set_endpoint_in_use()
            # Mark this retrieved endpoint as one that is in use
            api_endpoint.set_method_in_use(self.http_method)

    @gen.coroutine
    def create_lambda_api_route(self, task_spawner, api_gateway: ApiGatewayWorkflowState):
        logit(f"Setting up route {self.http_method} {self.api_path} for API Endpoint '{self.name}'...")

        # First we clean the Lambda of API Gateway policies which point
        # to dead API Gateways
        yield task_spawner.clean_lambda_iam_policies(
            self._credentials,
            self.name
        )

        path_parts = [part for part in self.api_path.split("/") if part != '']
        current_base_pointer_id = yield self.make_api_path_exist(task_spawner, api_gateway, path_parts)

        # Create method on base resource
        method_response = yield task_spawner.create_method(
            self._credentials,
            "HTTP Method",
            api_gateway.api_gateway_id,
            current_base_pointer_id,
            self.http_method,
            False,
        )

        # Link the API Gateway to the lambda
        link_response = yield task_spawner.link_api_method_to_lambda(
            self._credentials,
            api_gateway.api_gateway_id,
            current_base_pointer_id,
            self
        )

    @gen.coroutine
    def mark_lambda_api_route(self, task_spawner, api_gateway: ApiGatewayWorkflowState):
        pass

    def deploy(self, task_spawner, project_id, project_config):
        logit(f"Deploying API Endpoint '{self.name}'...")

        # TODO move this to predeploy
        self.execution_pipeline_id = project_id,
        self.execution_log_level = project_config["logging"]["level"]

        # TODO we also might want to check the api gateway to prove that the routes are also still setup?

        state_changed = self.state_has_changed()
        if not state_changed and self.deployed_state.exists:
            logit(f"{self.name} has not changed and is currently deployed, not redeploying")
            return None

        return self.deploy_lambda(task_spawner)
