from __future__ import annotations

import json
import traceback
import uuid
from _sha256 import sha256
from enum import Enum

from tornado import gen
from typing import Dict, Union, Type, List

from assistants.deployments.api_gateway import strip_api_gateway
from controller.aws.actions import get_language_specific_environment_variables, create_lambda_api_route, add_auto_warmup
from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
from pyexceptions.builds import BuildException
from utils.general import get_safe_workflow_state_name, logit, get_random_node_id


def get_layers_for_lambda(language):
	"""
	IGNORE THIS NOTICE AT YOUR OWN PERIL. YOU HAVE BEEN WARNED.

	All layers are managed under our root AWS account at 134071937287.

	When a new layer is published the ARNs must be updated in source intentionally
	so that whoever does so must read this notice and understand what MUST
	be done before updating the Refinery customer runtime for customers.

	You must do the following:
	* Extensively test the new custom runtime.
	* Upload the new layer version to the root AWS account.
	* Run the following command on the root account to publicly allow use of the layer:

	aws lambda add-layer-version-permission \
	--layer-name REPLACE_ME_WITH_LAYER_NAME \
	--version-number REPLACE_ME_WITH_LAYER_VERSION \
	--statement-id public \
	--action lambda:GetLayerVersion \
	--principal "*" \
	--region us-west-2

	* Test the layer in a development version of Refinery to ensure it works.
	* Update the source code with the new layer ARN

	Once this is done all future deployments will use the new layers.
	"""
	new_layers = []

	# Add the custom runtime layer in all cases
	if language == "nodejs8.10":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-node810-custom-runtime:30"
		)
	elif language == "nodejs10.16.3":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-nodejs10-custom-runtime:9"
		)
	elif language == "nodejs10.20.1":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-nodejs1020-custom-runtime:1"
		)
	elif language == "php7.3":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-php73-custom-runtime:28"
		)
	elif language == "go1.12":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-go112-custom-runtime:29"
		)
	elif language == "python2.7":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-python27-custom-runtime:28"
		)
	elif language == "python3.6":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-python36-custom-runtime:29"
		)
	elif language == "ruby2.6.4":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-ruby264-custom-runtime:29"
		)

	return new_layers


class DeploymentException(Exception):
	def __init__(self, node_id, name, node_type, msg):
		self.id = node_id
		self.name = name
		self.node_type = node_type
		self.msg = msg

	def __repr__(self):
		return f'name: {self.name}, id: {self.id}, type: {self.node_type}, exception:\n{self.msg}'


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


class TransitionTypes(Enum):
	IF = "if"
	ELSE = "else"
	EXCEPTION = "exception"
	THEN = "then"
	FAN_OUT = "fan-out"
	FAN_IN = "fan-in"
	MERGE = "merge"


class InvalidDeployment(Exception):
	pass


class WorkflowRelationship:
	def __init__(self, _id, _type, origin_node, next_node):
		self.id: str = _id
		self.type: TransitionTypes = _type
		self.origin_node: WorkflowState = origin_node
		self.next_node: WorkflowState = next_node

	def serialize(self, use_arns=True):
		origin_node_id = self.origin_node.arn if use_arns else self.origin_node.id
		next_node_id = self.next_node.arn if use_arns else self.next_node.id
		return {
			"id": self.id,
			"type": self.type.value,
			"node": origin_node_id,
			"next": next_node_id
		}


class IfWorkflowRelationship(WorkflowRelationship):
	def __init__(self, expression, *args, **kwargs):
		super(IfWorkflowRelationship, self).__init__(*args, **kwargs)
		self.expression = expression


class MergeWorkflowRelationship(WorkflowRelationship):
	def __init__(self, *args, **kwargs):
		super(MergeWorkflowRelationship, self).__init__(*args, **kwargs)
		self.merge_lambdas = []


class DeploymentDiagram:
	def __init__(self, project_id, project_name, project_config):
		self.project_id = project_id
		self.project_name = project_name
		self.project_config = project_config
		self.api_gateway: Union[ApiGatewayWorkflowState, None] = None

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
	def _await_deployments(self, deploy_futures):
		deployment_exceptions = []

		# Initialize list of results
		deployment_type_lookup: Dict[StateTypes, List] = {
			state_type: [] for state_type in StateTypes
		}

		for deploy_future_data in deploy_futures:
			try:
				output = yield deploy_future_data["future"]
				name = deploy_future_data["name"]
				logit(f"Deployed node '{name}' successfully!")

				deploy_state_type = deploy_future_data["type"]
				state_type = StateTypes(deploy_state_type)
				deployment_type_lookup[state_type].append(output)
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

		raise gen.Return({
			"deployment_type_lookup": deployment_type_lookup,
			"deployment_exceptions": deployment_exceptions
		})

	@gen.coroutine
	def _setup_api_endpoints(self, task_spawner, api_gateway_manager, credentials, deployed_api_endpoints):
		yield self.api_gateway.use_or_create_api_gateway(task_spawner, api_gateway_manager)

		api_gateway_id = self.api_gateway.api_gateway_id

		for deployed_api_endpoint in deployed_api_endpoints:
			try:
				workflow_state = self.lookup_workflow_state(deployed_api_endpoint["id"])
			except InvalidDeployment:
				logit("Unable to find api endpoint: " + deployed_api_endpoint["id"])
				continue

			assert isinstance(workflow_state, ApiEndpointWorkflowState)

			http_method = workflow_state.http_method
			api_path = workflow_state.api_path
			name = deployed_api_endpoint["name"]
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

		for deployed_workflow_state in deployed_workflow_states:
			workflow_state = self.lookup_workflow_state(deployed_workflow_state["id"])

			workflow_state.arn = deployed_workflow_state["arn"]
			workflow_state.name = deployed_workflow_state["name"]

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
	def deploy(self, task_spawner, api_gateway_manager, credentials, unique_deploy_id):
		deploy_futures = []
		for workflow_state in self._workflow_state_lookup.values():
			deploy_future = workflow_state.deploy(
				task_spawner, self.project_id, self.project_config)

			if deploy_future is None:
				continue

			deploy_futures.append(deploy_future)

		deploy_info = yield self._await_deployments(deploy_futures)
		deployment_type_lookup = deploy_info["deployment_type_lookup"]
		deployment_exceptions = deploy_info["deployment_exceptions"]

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
				unique_deploy_id,
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


class WorkflowState:
	def __init__(self, credentials, _id, name, _type, arn=None):
		self._credentials = credentials

		self.id: str = _id
		self.name: str = get_safe_workflow_state_name(name)
		self.type: StateTypes = _type
		self.arn = self.get_arn_name() if arn is None else arn

		self.transitions: Dict[TransitionTypes, List[WorkflowRelationship]] = {transition_type: [] for
																			   transition_type in TransitionTypes}

	def serialize(self):
		return {
			"id": self.id,
			"name": self.name,
			"type": self.type.value,
			"arn": self.arn
		}

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		pass

	def deploy(self, task_spawner, project_id, project_config):
		pass

	def get_arn_name(self):
		name_prefix = ''
		if isinstance(self, LambdaWorkflowState) or isinstance(self, ApiEndpointWorkflowState):
			arn_type = 'lambda'
			name_prefix = 'function:'
		elif isinstance(self, SnsTopicWorkflowState):
			arn_type = 'sns'
		elif isinstance(self, SqsQueueWorkflowState):
			arn_type = 'sqs'
		elif isinstance(self, ScheduleTriggerWorkflowState):
			arn_type = 'events'
			name_prefix = 'rule/'
		else:
			# For pseudo-nodes like API Responses we don't need to create a teardown entry
			return None

		region = self._credentials["region"]
		account_id = self._credentials["account_id"]

		# Set ARN on workflow state
		return f'arn:aws:{arn_type}:{region}:{account_id}:{name_prefix}{self.name}'

	def create_transition(self, deploy_diagram: DeploymentDiagram, transition_type: TransitionTypes,
						  next_node: WorkflowState, workflow_relationship_json: Dict):
		if transition_type == TransitionTypes.IF:
			relationship = IfWorkflowRelationship(
				workflow_relationship_json["expression"],
				workflow_relationship_json["id"],
				transition_type,
				self,
				next_node
			)
		elif transition_type == TransitionTypes.MERGE:
			relationship = MergeWorkflowRelationship(
				workflow_relationship_json["id"],
				transition_type,
				self,
				next_node
			)
			deploy_diagram.add_node_to_merge_transition(self, next_node)
		else:
			relationship = WorkflowRelationship(
				workflow_relationship_json["id"],
				transition_type,
				self,
				next_node
			)

		self.transitions[transition_type].append(relationship)

	def set_merge_siblings_for_target(self, next_node_id, arn_list):
		"""
		In the case with merge transitions, we need all of the sibilings to
		know of each other, for example take this:

		[a] [b] [c]
		 \  |  /
		  \ | /
		   [d]

		The edges (a, d), (b, d), (c, d) are all merge transitions, we must tell
		a, b, c of each other.

		:param next_node_id: The connected node in the transition (in the example this is 'd')
		:param arn_list: arns of sibling blocks
		:return:
		"""
		for merge_transition in self.transitions[TransitionTypes.MERGE]:
			if merge_transition.next_node.id == next_node_id:
				merge_transition.merge_lambdas = arn_list
				break


class WarmerTriggerWorkflowState(WorkflowState):
	pass


class TriggerWorkflowState(WorkflowState):
	# TODO make abstract
	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		return None

	def link_deployed_triggers_to_next_state(self, task_spawner):
		deploy_trigger_futures = []

		for transition_type, transitions in self.transitions.items():
			for transition in transitions:

				future = self._link_trigger_to_next_deployed_state(
					task_spawner, transition.next_node)

				if future is not None:
					deploy_trigger_futures.append(future)

		return deploy_trigger_futures


class LambdaWorkflowState(WorkflowState):
	def __init__(self, credentials, _id, name, _type, is_inline_execution=False):
		super(LambdaWorkflowState, self).__init__(credentials, _id, name, _type)

		self.language = None
		self.code = None
		self.max_execution_time = None
		self.memory = None
		self.execution_pipeline_id = None
		self.execution_log_level = None
		self.reserved_concurrency_count = False
		self.layers = None
		self.libraries = None
		self.is_inline_execution = is_inline_execution

		self.execution_mode = "REGULAR"
		self.vpc_data = {}
		self.tags_dict = {
			"RefineryResource": "true"
		}
		self.environment_variables = {}
		self.shared_files_list = []

		# If it's a self-hosted (THIRDPARTY) AWS account we deploy with a different role
		# name which they manage themselves.
		if credentials["account_type"] == "THIRDPARTY":
			self.role = "arn:aws:iam::" + str(credentials["account_id"]) + ":role/" + THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
		else:
			self.role = "arn:aws:iam::" + str(credentials["account_id"]) + ":role/refinery_default_aws_lambda_role"

		self._workflow_files: List = []

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		self.execution_pipeline_id = deploy_diagram.project_id
		self.execution_log_level = deploy_diagram.project_config["logging"]["level"]

		if self.is_inline_execution:
			self.environment_variables = workflow_state_json["environment_variables"]
		else:
			env_vars = self._get_project_env_vars(deploy_diagram, workflow_state_json)
			self._set_environment_variables_for_lambda(env_vars)

		if "shared_files" in workflow_state_json:
			self.shared_files_list = workflow_state_json["shared_files"]
		else:
			self.shared_files_list = deploy_diagram.lookup_workflow_files(self.id)

		self.language = workflow_state_json["language"]
		self.code = workflow_state_json["code"]
		self.libraries = workflow_state_json["libraries"]
		self.max_execution_time = workflow_state_json["max_execution_time"]
		self.memory = workflow_state_json["memory"]
		self.layers = workflow_state_json["layers"]

		if "reserved_concurrency_count" in workflow_state_json:
			self.reserved_concurrency_count = workflow_state_json["reserved_concurrency_count"]

	def _set_environment_variables_for_lambda(self, env_vars):
		# Add environment variables depending on language
		# This is mainly for module loading when we're doing inline executions.
		language_specifc_env_vars = get_language_specific_environment_variables(
			self.language
		)

		all_environment_vars = {
			"REDIS_HOSTNAME": self._credentials["redis_hostname"],
			"REDIS_PASSWORD": self._credentials["redis_password"],
			"REDIS_PORT": str(self._credentials["redis_port"]),
			"EXECUTION_PIPELINE_ID": self.execution_pipeline_id,
			"LOG_BUCKET_NAME": self._credentials["logs_bucket"],
			"PACKAGES_BUCKET_NAME": self._credentials["lambda_packages_bucket"],
			"PIPELINE_LOGGING_LEVEL": self.execution_log_level,
			"EXECUTION_MODE": self.execution_mode,
			**language_specifc_env_vars,
			**env_vars
		}

		if self.is_inline_execution:
			# The environment variable activates it as
			# an inline execution Lambda and allows us to
			# pass in arbitrary code to execution.
			all_environment_vars["IS_INLINE_EXECUTOR"] = "True"

		self.environment_variables = all_environment_vars

	def _get_project_env_vars(self, deploy_diagram: DeploymentDiagram, workflow_state_json):
		workflow_state_env_vars = []

		tmp_env_vars: Dict[str, Dict[str, str]] = {
			env_var_uuid: env_var
			for env_var_uuid, env_var in workflow_state_json["environment_variables"].items()
		}

		project_env_vars = deploy_diagram.project_config["environment_variables"]
		for env_var_uuid, env_data in tmp_env_vars.items():
			project_env_var = project_env_vars.get(env_var_uuid)

			if project_env_var is None:
				continue

			# Add value to match schema
			tmp_env_vars[env_var_uuid]["value"] = project_env_var["value"]

			workflow_state_env_vars.append({
				"key": tmp_env_vars[env_var_uuid]["name"],
				"value": project_env_var["value"]
			})

		deploy_diagram.set_env_vars_for_workflow_state(self, workflow_state_env_vars)

		return {
			env_var["name"]: env_var["value"]
			for _, env_var in tmp_env_vars.items()
		}

	def set_transition_env_data(self):
		env_transitions = {
			transition_type.value: [t.serialize() for t in transitions_for_type]
			for transition_type, transitions_for_type in self.transitions.items()
		}
		self.environment_variables["TRANSITION_DATA"] = json.dumps(env_transitions)

	@gen.coroutine
	def deploy_lambda(self, task_spawner):
		logit(
			f"Deploying '{self.name}' Lambda package to production..."
		)

		# Don't yield for it, but we'll also create a log group at the same time
		# We're set a tag for that log group for cost tracking
		task_spawner.create_cloudwatch_group(
			self._credentials,
			f"/aws/lambda/{self.name}",
			{
				"RefineryResource": "true"
			},
			7
		)

		deployed_lambda_data = yield task_spawner.deploy_aws_lambda(
			self._credentials,
			self
		)

		# If we have concurrency set, then we'll set that for our deployed Lambda
		if self.reserved_concurrency_count:
			logit("Setting reserved concurrency for Lambda '" +
				  deployed_lambda_data["FunctionArn"] +
				  "' to " +
				  str(self.reserved_concurrency_count) +
				  "...")
			yield task_spawner.set_lambda_reserved_concurrency(
				self._credentials,
				deployed_lambda_data["FunctionArn"],
				self.reserved_concurrency_count
			)

		raise gen.Return({
			"id": self.id,
			"name": self.name,
			"arn": deployed_lambda_data["FunctionArn"]
		})

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying Lambda '{self.name}'...")

		self.set_transition_env_data()

		self.layers = get_layers_for_lambda(
			self.language
		) + self.layers

		# TODO we could probably clean up this interface
		return {
			"id": self.id,
			"name": self.name,
			"type": self.type,
			"future": self.deploy_lambda(task_spawner)
		}

	def get_hash_key(self):
		hash_dict = {
			"language": self.language,
			"timeout": self.max_execution_time,
			"memory": self.memory,
			"environment_variables": self.environment_variables,
			"layers": self.layers
		}

		# For Go we don't include the libraries in the inline Lambda
		# hash key because the final binary is built in ECS before
		# being pulled down by the inline Lambda.
		if self.language != "go1.12":
			hash_dict["libraries"] = self.libraries

		return sha256(
			json.dumps(
				hash_dict,
				sort_keys=True
			).encode('utf-8')
		).hexdigest()


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

		print(self.api_gateway_id, api_gateway_exists)

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

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		self.http_method = workflow_state_json["http_method"]
		self.api_path = workflow_state_json["api_path"]

	def set_api_url(self, api_gateway_id):
		self.rest_api_id = api_gateway_id
		region = self._credentials["region"]
		api_path = self.api_path
		self.url = f"https://{api_gateway_id}.execute-api.{region}.amazonaws.com/refinery{api_path}"

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying API Endpoint '{self.name}'...")

		lambda_layers = get_layers_for_lambda("python2.7")

		self.set_transition_env_data()

		self.language = "python2.7"
		self.code = ""
		self.libraries = []
		self.max_execution_time = 30
		self.memory = 512
		self.execution_mode = "API_ENDPOINT",
		self.execution_pipeline_id = project_id,
		self.execution_log_level = project_config["logging"]["level"],
		self.environment_variables = {}
		self.layers = lambda_layers
		self.reserved_concurrency_count = False
		self.is_inline_execution = False
		self.shared_files_list = []

		return {
			"id": self.id,
			"name": self.name,
			"type": self.type,
			"future": self.deploy_lambda(task_spawner)
		}


class ScheduleTriggerWorkflowState(TriggerWorkflowState):
	def __init__(self, *args, **kwargs):
		super(ScheduleTriggerWorkflowState, self).__init__(*args, **kwargs)

		self.schedule_expression = None
		self.description = None
		self.input_string = None

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		self.schedule_expression = workflow_state_json["schedule_expression"]
		self.description = workflow_state_json["description"]
		self.input_string = workflow_state_json["input_string"]

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying schedule trigger '{self.name}'...")
		return {
			"id": self.id,
			"name": self.name,
			"type": self.type,
			"future": task_spawner.create_cloudwatch_rule(
				self._credentials,
				self.id,
				self.name,
				self.schedule_expression,
				self.description,
				self.input_string
			)
		}

	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		print(self.name, next_node.name, next_node.arn)
		return task_spawner.add_rule_target(
			self._credentials,
			self.name,
			next_node.name,
			next_node.arn,
			self.input_string
		)


class SqsQueueWorkflowState(TriggerWorkflowState):
	def __init__(self, *args, **kwargs):
		super(SqsQueueWorkflowState, self).__init__(*args, **kwargs)

		self.batch_size = None

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, str]):
		try:
			self.batch_size = int(workflow_state_json["batch_size"])
		except ValueError:
			raise InvalidDeployment(f"unable to parse 'batch_size' for SQS Queue: {self.name}")

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying SQS queue '{self.name}'...")
		return {
			"id": self.id,
			"name": self.name,
			"type": self.type,
			"future": task_spawner.create_sqs_queue(
				self._credentials,
				self.id,
				self.name,
				int(self.batch_size),  # Not used, passed along
				900  # Max Lambda runtime - TODO set this to the linked Lambda amount
			)
		}

	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		return task_spawner.map_sqs_to_lambda(
			self._credentials,
			self.arn,
			next_node.arn,
			self.batch_size
		)


class SnsTopicWorkflowState(TriggerWorkflowState):
	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying SNS topic '{self.name}'...")

		return {
			"id": self.id,
			"name": self.name,
			"type": self.type,
			"future": task_spawner.create_sns_topic(
				self._credentials,
				self.id,
				self.name
			)
		}

	def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
		return task_spawner.subscribe_lambda_to_sns_topic(
			self._credentials,
			self.arn,
			next_node.arn,
		)


WorkflowStateTypes = Type[Union[
	LambdaWorkflowState, ApiEndpointWorkflowState, SqsQueueWorkflowState,
	SnsTopicWorkflowState, ScheduleTriggerWorkflowState
]]


def workflow_state_from_json(credentials, deploy_diagram: DeploymentDiagram,
							 workflow_state_json: Dict) -> WorkflowState:
	node_id = workflow_state_json["id"]
	node_type = workflow_state_json["type"]

	try:
		state_type = StateTypes(workflow_state_json["type"])
	except ValueError as e:
		raise InvalidDeployment(f"workflow state {node_id} has invalid type {node_type}")

	state_type_to_workflow_state: Dict[StateTypes, WorkflowStateTypes] = {
		StateTypes.LAMBDA: LambdaWorkflowState,
		StateTypes.API_ENDPOINT: ApiEndpointWorkflowState,
		StateTypes.SQS_QUEUE: SqsQueueWorkflowState,
		StateTypes.SNS_TOPIC: SnsTopicWorkflowState,
		StateTypes.SCHEDULE_TRIGGER: ScheduleTriggerWorkflowState,
		StateTypes.API_GATEWAY_RESPONSE: ApiGatewayResponseWorkflowState
	}

	workflow_state_type = state_type_to_workflow_state.get(state_type)

	if workflow_state_json is None:
		raise InvalidDeployment(f"invalid workflow state type: {state_type} for workflow state: {node_id}")

	workflow_state = workflow_state_type(
		credentials,
		workflow_state_json.get("id"),
		workflow_state_json.get("name"),
		state_type
	)

	workflow_state.setup(deploy_diagram, workflow_state_json)

	return workflow_state


def workflow_relationship_from_json(deploy_diagram: DeploymentDiagram, workflow_relationship_json: Dict):
	try:
		relation_type = TransitionTypes(workflow_relationship_json["type"])
	except ValueError as e:
		relation_id = workflow_relationship_json["id"]
		relation_type = workflow_relationship_json["type"]
		raise InvalidDeployment(f"workflow relationship {relation_id} has invalid type {relation_type}")

	origin_node_id = workflow_relationship_json["node"]
	next_node_id = workflow_relationship_json["next"]

	origin_node = deploy_diagram.lookup_workflow_state(origin_node_id)
	next_node = deploy_diagram.lookup_workflow_state(next_node_id)

	origin_node.create_transition(
		deploy_diagram, relation_type, next_node, workflow_relationship_json)
