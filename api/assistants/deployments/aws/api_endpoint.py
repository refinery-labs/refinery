from __future__ import annotations

from assistants.deployments.aws.utils import get_layers_for_lambda
from assistants.deployments.diagram.endpoint import EndpointWorkflowState
from assistants.deployments.aws.lambda_function import LambdaWorkflowState
from utils.general import logit

API_GATEWAY_STATE_NAME = "__api_gateway__"
API_GATEWAY_STATE_ARN = "API_GATEWAY"
API_GATEWAY_STAGE_NAME = "refinery"


class ApiEndpointWorkflowState(EndpointWorkflowState, LambdaWorkflowState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def deploy(self, task_spawner, project_id, project_config):
        logit(f"Deploying API Endpoint '{self.name}'...")

        state_changed = self.state_has_changed()
        if not state_changed and self.deployed_state.exists:
            logit(f"{self.name} has not changed and is currently deployed, not redeploying")
            return None

        return self.deploy_lambda(task_spawner)
