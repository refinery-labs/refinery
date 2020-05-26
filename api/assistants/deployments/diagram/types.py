from __future__ import annotations

from enum import Enum

from tornado import gen
from typing import List, Dict, TYPE_CHECKING, Union

if TYPE_CHECKING:
	from assistants.deployments.diagram.api_endpoint_workflow_states import ApiEndpointWorkflowState
	from assistants.deployments.diagram.workflow_states import WorkflowState


class StateTypes(Enum):
	INVALID = "invalid"
	LAMBDA = "lambda"
	SQS_QUEUE = "sqs_queue"
	SNS_TOPIC = "sns_topic"
	SCHEDULE_TRIGGER = "schedule_trigger"
	API_ENDPOINT = "api_endpoint"
	API_GATEWAY_RESPONSE = "api_gateway_response"
	API_GATEWAY = "api_gateway"
	WARMER_TRIGGER = "warmer_trigger"


class RelationshipTypes(Enum):
	IF = "if"
	ELSE = "else"
	EXCEPTION = "exception"
	THEN = "then"
	FAN_OUT = "fan-out"
	FAN_IN = "fan-in"
	MERGE = "merge"


class LambdaEventSourceMapping:
	def __init__(self, uuid, event_source_arn):
		self.uuid = uuid
		self.event_source_arn = event_source_arn


class TopicSubscription:
	def __init__(self, subscription_arn, endpoint):
		self.subscription_arn = subscription_arn
		self.endpoint = endpoint


class CloudwatchRuleTarget:
	def __init__(self, arn):
		self.arn = arn


class DeploymentState:
	def __init__(self, state_type: StateTypes, arn: str, state_hash: Union[str, None]):
		self.type: StateTypes = state_type
		self.arn: str = arn
		self.state_hash: Union[str, None] = state_hash

		self.exists: bool = False

	def __str__(self):
		return f'Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}'

	def state_changed(self, current_state: DeploymentState):
		return self.state_hash != current_state.state_hash


class LambdaDeploymentState(DeploymentState):
	def __init__(self, state_type, arn, state_hash):
		super(LambdaDeploymentState, self).__init__(state_type, arn, state_hash)

		self.event_source_mappings: List[LambdaEventSourceMapping] = []

	def __str__(self):
		return f'Lambda Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}, event_source_mappings: {self.event_source_mappings}'

	def is_linked_to_trigger(self, trigger_state: WorkflowState):
		return any([mapping.event_source_arn == trigger_state.arn for mapping in self.event_source_mappings])


class ApiGatewayEndpoint:
	def __init__(self, _id, path):
		self.id = _id
		self.path = path

		# map HTTP methods to whether or not they are in use
		self._methods: Dict[str, bool] = dict()

	def set_method_in_use(self, method):
		self._methods[method] = True

	def get_methods_to_be_removed(self):
		return [method for method, in_use in self._methods.items() if not in_use]

	def endpoint_can_be_removed(self):
		# if all of the methods are not being used, then we can remove this
		return all([not in_use for in_use in self._methods.values()])


class ApiGatewayLambdaConfig:
	def __init__(self, method, path):
		self.method = method
		self.path = path

	def matches_expected_state(self, api_endpoint: ApiEndpointWorkflowState):
		return self.method == api_endpoint.http_method and self.path == api_endpoint.api_path


class ApiGatewayDeploymentState(DeploymentState):
	def __init__(self, state_type, arn, state_hash, api_gateway_id=None):
		super(ApiGatewayDeploymentState, self).__init__(state_type, arn, state_hash)

		self.api_gateway_id = api_gateway_id

		self.base_resource_id = None
		self.stages = []
		self._path_existence_map: Dict[str, ApiGatewayEndpoint] = {}
		self._configured_lambdas: Dict[str, ApiGatewayLambdaConfig] = {}

	def add_endpoint(self, api_endpoint: ApiGatewayEndpoint):
		self._path_existence_map[api_endpoint.path] = api_endpoint

	def add_configured_lambda(self, lambda_uri, lambda_config):
		self._configured_lambdas[lambda_uri] = lambda_config

	def get_endpoint_from_path(self, path: str) -> ApiGatewayEndpoint:
		return self._path_existence_map.get(path)

	@gen.coroutine
	def remove_unused_resources(self, api_gateway_manager, credentials, api_gateway_id):
		deletion_futures = []
		for api_endpoint in self._path_existence_map.values():
			methods = api_endpoint.get_methods_to_be_removed()
			for method in methods:
				future = api_gateway_manager.delete_rest_api_resource_method(
					credentials,
					api_gateway_id,
					api_endpoint.id,
					method
				)
				deletion_futures.append(future)

			if api_endpoint.endpoint_can_be_removed():
				future = api_gateway_manager.delete_rest_api_resource(
					credentials,
					api_gateway_id,
					api_endpoint.id
				)
				deletion_futures.append(future)

		yield deletion_futures

	def endpoint_is_configured(self, task_spawner, credentials, api_endpoint: ApiEndpointWorkflowState) -> bool:
		lambda_uri = task_spawner.get_lambda_uri_for_api_method(credentials, api_endpoint)

		configured_lambda = self._configured_lambdas.get(lambda_uri)
		if configured_lambda is None:
			return False

		return configured_lambda.matches_expected_state(api_endpoint)

	def __str__(self):
		return f'Api Gateway Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}, api gateway id: {self.api_gateway_id}'


class SnsTopicDeploymentState(DeploymentState):
	def __init__(self, state_type, arn, state_hash):
		super(SnsTopicDeploymentState, self).__init__(state_type, arn, state_hash)

		self.subscriptions: List[TopicSubscription] = []

	def __str__(self):
		return f'Sns Topic Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}, subscriptions: {self.subscriptions}'


class ScheduleTriggerDeploymentState(DeploymentState):
	def __init__(self, state_type, arn, state_hash):
		super(ScheduleTriggerDeploymentState, self).__init__(state_type, arn, state_hash)

		self.rules: List[CloudwatchRuleTarget] = []

	def __str__(self):
		return f'Schedule Trigger Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}, rules: {self.rules}'
