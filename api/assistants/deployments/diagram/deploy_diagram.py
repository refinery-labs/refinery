import json
import traceback

from tornado import gen
from typing import Union, Dict, List

from assistants.deployments.diagram.api_endpoint_workflow_states import ApiGatewayWorkflowState, \
	ApiEndpointWorkflowState
from assistants.deployments.diagram.errors import InvalidDeployment
from assistants.deployments.diagram.trigger_workflow_states import TriggerWorkflowState, WarmerTriggerWorkflowState
from assistants.deployments.diagram.utils import create_lambda_api_route, add_auto_warmup
from assistants.deployments.diagram.workflow_states import WorkflowState, StateTypes, DeploymentException
from pyexceptions.builds import BuildException
from utils.general import get_random_deploy_id, logit


class DeploymentDiagram:
	def __init__(self, project_id, project_name, project_config, latest_deployment=None):
		self.project_id = project_id
		self.project_name = project_name
		self.project_config = project_config
		self.api_gateway: Union[ApiGatewayWorkflowState, None] = None

		self._previous_state_lookup = None
		if latest_deployment is not None and "workflow_states" in latest_deployment:
			self._previous_state_lookup = {ws.id: ws.get("hash") for ws in latest_deployment["workflow_states"]}

		self._unique_deploy_id = get_random_deploy_id()
		self._unique_counter = 0
		self._workflow_file_lookup: Dict[str, List] = {}
		self._workflow_state_lookup: Dict[str, WorkflowState] = {}
		self._merge_workflow_relationship_lookup: Dict = {}
		self._workflow_state_env_vars: Dict = {}

	def serialize(self):
		workflow_states: [Dict] = []
		workflow_relationships: [Dict] = []

		for ws in self._workflow_state_lookup.values():
			workflow_states.append(ws.serialize())
			for transition_type_transitions in ws.transitions.values():
				workflow_relationships.extend(
					[transition.serialize(use_arns=False) for transition in transition_type_transitions]
				)

		return {
			"name": self.project_name,
			"project_id": self.project_id,
			"workflow_states": workflow_states,
			"workflow_relationships": workflow_relationships,
		}

	def get_previous_state(self, state_id):
		if self._previous_state_lookup is None:
			return None
		return self._previous_state_lookup.get(state_id)

	def get_unique_workflow_state_name(self):
		return self._unique_deploy_id + str(self._unique_counter)

	def initialize_api_gateway(self, credentials):
		self.api_gateway = ApiGatewayWorkflowState(credentials)

		# If for some reason we have an api gateway id in the config but not
		# included as a workflow state, we set that up here
		if self.project_config["api_gateway"]["gateway_id"]:
			self.api_gateway.setup(self, self.project_config)

	def add_workflow_files(self, workflow_file_links_json, workflow_files_json):
		workflow_file_lookup = {}
		for workflow_file_json in workflow_files_json:
			workflow_file_lookup[workflow_file_json["id"]] = workflow_file_json

		for workflow_file_link_json in workflow_file_links_json:
			file_id = workflow_file_link_json["file_id"]
			workflow_file = workflow_file_lookup.get(file_id)
			if workflow_file is None:
				raise InvalidDeployment(f"no workflow_file found with ID: {file_id}")

			node_id = workflow_file_link_json["node"]
			node_files = self._workflow_file_lookup.get(node_id)
			if node_files is not None:
				node_files.append(workflow_file)
			else:
				self._workflow_file_lookup[node_id] = [workflow_file]

	def add_workflow_state(self, workflow_state: WorkflowState):
		self._workflow_state_lookup[workflow_state.id] = workflow_state

	def add_node_to_merge_transition(self, origin_node: WorkflowState, next_node: WorkflowState):
		existing_next_nodes = self._merge_workflow_relationship_lookup.get(next_node.id)
		if existing_next_nodes:
			existing_next_nodes.append(origin_node.id)
		else:
			self._merge_workflow_relationship_lookup[next_node.id] = [origin_node.id]

	def finalize_merge_transitions(self):
		for next_node_id, origin_node_ids in self._merge_workflow_relationship_lookup.items():
			arn_list = []
			origin_nodes = []
			for origin_node_id in origin_node_ids:
				origin_node = self._workflow_state_lookup[origin_node_id]
				arn_list.append(origin_node.arn)
				origin_nodes.append(origin_node)

			for origin_node in origin_nodes:
				origin_node.set_merge_siblings_for_target(next_node_id, arn_list)

	def set_env_vars_for_workflow_state(self, workflow_state: WorkflowState, env_vars: [str]):
		self._workflow_state_env_vars[workflow_state.id] = env_vars

	def update_workflow_state(self, workflow):
		pass

	def lookup_workflow_state(self, node_id) -> WorkflowState:
		ws = self._workflow_state_lookup.get(node_id)
		if ws is None:
			raise InvalidDeployment(f"Unable to find {node_id} in project")

		return ws

	def lookup_workflow_files(self, node_id) -> List[Dict]:
		files = self._workflow_file_lookup.get(node_id)
		if files is None:
			return []

		return files

	@gen.coroutine
	def _setup_api_endpoints(self, task_spawner, api_gateway_manager, credentials, deployed_api_endpoints):
		yield self.api_gateway.use_or_create_api_gateway(task_spawner, api_gateway_manager)

		api_gateway_id = self.api_gateway.api_gateway_id

		for api_endpoint in deployed_api_endpoints:
			assert isinstance(api_endpoint, ApiEndpointWorkflowState)

			http_method = api_endpoint.http_method
			api_path = api_endpoint.api_path
			name = api_endpoint.name
			print(f"Setting up route {http_method} {api_path} for API Endpoint '{name}'...")

			yield create_lambda_api_route(
				task_spawner,
				api_gateway_manager,
				credentials,
				api_gateway_id,
				http_method,
				api_path,
				name,
				True
			)

		logit("Now deploying API gateway to stage...")
		deploy_stage_results = yield task_spawner.deploy_api_gateway_to_stage(
			credentials,
			api_gateway_id,
			"refinery"
		)
	# TODO check deploy_stage_results?

	def _update_workflow_states_with_deploy_info(self, task_spawner, deployed_workflow_states):
		update_futures = []

		for workflow_state in deployed_workflow_states:
			if isinstance(workflow_state, ApiEndpointWorkflowState):
				api_gateway_id = self.api_gateway.api_gateway_id
				workflow_state.set_api_url(api_gateway_id)

			elif isinstance(workflow_state, TriggerWorkflowState):
				# If this workflow state feels triggered, calm it down by associating it with its deployed children
				workflow_state_futures = workflow_state.link_deployed_triggers_to_next_state(task_spawner)
				update_futures.extend(workflow_state_futures)

		return update_futures

	@gen.coroutine
	def _create_auto_warmers(
			self,
			task_spawner,
			credentials,
			unique_deploy_id,
			warmup_concurrency_level,
			deployment_type_lookup
	):
		deployed_lambda_states = deployment_type_lookup[StateTypes.LAMBDA]
		deployed_api_endpoints = deployment_type_lookup[StateTypes.API_ENDPOINT]

		combined_warmup_list = json.loads(
			json.dumps(
				[state.serialize() for state in deployed_lambda_states]
			)
		)
		combined_warmup_list = combined_warmup_list + json.loads(
			json.dumps(
				[state.serialize() for state in deployed_api_endpoints]
			)
		)
		logit("Adding auto-warming to the deployment...")

		warmup_concurrency_level = int(warmup_concurrency_level)
		warmer_triggers_data = yield add_auto_warmup(
			task_spawner,
			credentials,
			warmup_concurrency_level,
			unique_deploy_id,
			combined_warmup_list
		)

		for warmer_trigger in warmer_triggers_data:
			warmer_id = warmer_trigger["id"]
			name = warmer_trigger["name"]
			arn = warmer_trigger["arn"]

			warmer_trigger_state = WarmerTriggerWorkflowState(
				None, warmer_id, name, StateTypes.WARMER_TRIGGER, arn=arn)
			self.add_workflow_state(warmer_trigger_state)

	@gen.coroutine
	def deploy(self, task_spawner, api_gateway_manager, credentials):
		deploy_futures = []
		for workflow_state in self._workflow_state_lookup.values():
			deploy_future = workflow_state.deploy(
				task_spawner, self.project_id, self.project_config)

			if deploy_future is None:
				continue

			deploy_futures.append({
				"future": deploy_future,
				"workflow_state": workflow_state
			})

		deployment_exceptions = []

		# Initialize list of results
		deployment_type_lookup: Dict[StateTypes, List] = {
			state_type: [] for state_type in StateTypes
		}

		for deploy_future_data in deploy_futures:
			try:
				yield deploy_future_data["future"]
				ws = deploy_future_data["workflow_state"]
				logit(f"Deployed node '{ws.name}' successfully!")

				deployment_type_lookup[ws.type].append(ws)
			except Exception as e:
				# TODO be more explicit about handled errors

				logit("Failed to deploy node '" + deploy_future_data["name"] + "'!", "error")

				if isinstance(e, ValueError):
					# TODO handle this case
					pass

				exception_msg = traceback.format_exc()
				if isinstance(e, BuildException):
					# noinspection PyUnresolvedReferences
					exception_msg = e.build_output

				logit("Deployment failure exception details: " + repr(exception_msg), "error")
				deployment_exceptions.append(DeploymentException(
					deploy_future_data["id"],
					deploy_future_data["name"],
					deploy_future_data["type"],
					exception_msg
				))

		if len(deployment_exceptions) != 0:
			raise gen.Return({
				"deployment_exceptions": deployment_exceptions
			})

		if len(deployment_type_lookup[StateTypes.API_ENDPOINT]) > 0:
			deployed_api_endpoints = deployment_type_lookup[StateTypes.API_ENDPOINT]
			yield self._setup_api_endpoints(
				task_spawner, api_gateway_manager, credentials, deployed_api_endpoints)

		update_futures = []
		for state_type in StateTypes:
			deployed_workflow_states = deployment_type_lookup[state_type]
			update_futures = self._update_workflow_states_with_deploy_info(task_spawner, deployed_workflow_states)

		warmup_concurrency_level = self.project_config.get("warmup_concurrency_level")
		if warmup_concurrency_level:
			yield self._create_auto_warmers(
				task_spawner,
				credentials,
				self._unique_deploy_id,
				warmup_concurrency_level,
				deployment_type_lookup
			)

		yield update_futures

		raise gen.Return([])

	def get_workflow_states_for_teardown(self) -> [Dict]:
		nodes = []
		for workflow_state in self._workflow_state_lookup.values():
			nodes.append({
				workflow_state.id,
				workflow_state.arn,
				workflow_state.name,
				workflow_state.type.value
			})
		return nodes
