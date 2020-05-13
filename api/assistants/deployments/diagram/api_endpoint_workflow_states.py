from __future__ import annotations

import uuid

from tornado import gen
from typing import Dict, TYPE_CHECKING

from assistants.deployments.api_gateway import strip_api_gateway
from assistants.deployments.diagram.lambda_workflow_state import LambdaWorkflowState
from assistants.deployments.diagram.utils import get_layers_for_lambda
from assistants.deployments.diagram.workflow_states import WorkflowState, StateTypes
from utils.general import get_random_node_id, logit

if TYPE_CHECKING:
	from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


class ApiGatewayResponseWorkflowState(WorkflowState):
	pass


class ApiGatewayWorkflowState(WorkflowState):
	def __init__(self, credentials):
		super(ApiGatewayWorkflowState, self).__init__(
			credentials,
			get_random_node_id(),
			"__api_gateway__",
			StateTypes.API_GATEWAY
		)

		self.project_id = ""
		self.api_gateway_id = None

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		gateway_id = deploy_diagram.project_config["api_gateway"]["gateway_id"]
		if not gateway_id:
			return

		self.api_gateway_id = gateway_id
		self.project_id = deploy_diagram.project_id

		# set the api gateway for this deployment since it already exists
		deploy_diagram.api_gateway = self

	@gen.coroutine
	def use_or_create_api_gateway(self, task_spawner, api_gateway_manager):
		api_gateway_exists = False

		if self.api_gateway_id is not None:
			logit("Verifying existence of API Gateway...")
			api_gateway_exists = yield api_gateway_manager.api_gateway_exists(
				self._credentials,
				self.api_gateway_id
			)

		if self.api_gateway_id is None or not api_gateway_exists:
			# We need to create an API gateway
			logit("Deploying API Gateway for API Endpoint(s)...")

			# We just generate a random ID for the API Gateway, no great other way to do it.
			# e.g. when you change the project name now it's hard to know what the API Gateway
			# is...
			formatted_uuid = str(uuid.uuid4()).replace(
				"-",
				""
			)
			rest_api_name = f"Refinery-API-Gateway_{formatted_uuid}"

			create_gateway_result = yield task_spawner.create_rest_api(
				self._credentials,
				rest_api_name,
				"API Gateway created by Refinery. Associated with project ID " + self.project_id,
				"1.0.0"
			)

			self.api_gateway_id = create_gateway_result["id"]
		else:
			# We do another strip of the gateway just to be sure
			yield strip_api_gateway(
				api_gateway_manager,
				self._credentials,
				self.api_gateway_id
			)


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
		serialized_ws_state = WorkflowState.serialize(self)
		return {
			**serialized_ws_state,
			"url": self.url,
			"rest_api_id": self.rest_api_id,
			"http_method": self.http_method,
			"api_path": self.api_path
		}

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		self.http_method = workflow_state_json["http_method"]
		self.api_path = workflow_state_json["api_path"]

		self.execution_pipeline_id = deploy_diagram.project_id
		self.execution_log_level = deploy_diagram.project_config["logging"]["level"]
		self.execution_mode = "API_ENDPOINT"

		self._set_environment_variables_for_lambda({})

		self.set_name(self.name + deploy_diagram.get_unique_workflow_state_name())

	def set_api_url(self, api_gateway_id):
		self.rest_api_id = api_gateway_id
		region = self._credentials["region"]
		api_path = self.api_path
		self.url = f"https://{api_gateway_id}.execute-api.{region}.amazonaws.com/refinery{api_path}"

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying API Endpoint '{self.name}'...")

		self.set_transition_env_data()

		self.execution_pipeline_id = project_id,
		self.execution_log_level = project_config["logging"]["level"],

		return self.deploy_lambda(task_spawner)

