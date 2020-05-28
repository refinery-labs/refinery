import json
import traceback
import uuid

from tornado import gen
from typing import Union, Dict, List, Generic, TypeVar

from assistants.deployments.diagram.errors import InvalidDeployment, DeploymentException
from assistants.deployments.diagram.new_workflow_object import workflow_state_from_json, workflow_relationship_from_json
from assistants.deployments.diagram.workflow_states import WorkflowState, StateLookup
from pyexceptions.builds import BuildException
from utils.general import logit


class DeploymentDiagram:
	"""
	DeploymentDiagram represents high level actions which are performed in regards to the deployment of a
	user created graph.

	The deployment diagram will diff the existing infrastructure which exists with that that needs to be deployed.
	The comparison of state for each component of a deployment is delegated to each component.
	"""

	def __init__(self, project_id, project_name, project_config, task_spawner, credentials):
		self.project_id = project_id
		self.project_name = project_name
		self.project_config = project_config
		self.task_spawner = task_spawner
		self.credentials = credentials

		self._unique_deploy_id = "random"

		self._workflow_file_lookup: Dict[str, List] = {}
		self._workflow_state_lookup: StateLookup[WorkflowState] = StateLookup[WorkflowState]()
		self._merge_workflow_relationship_lookup: Dict = {}
		self._workflow_state_env_vars: Dict = {}

	def serialize(self):
		return {
			"name": self.project_name,
			"project_id": self.project_id,
		}

	def add_workflow_files(self, workflow_files_json, workflow_file_links_json):
		workflow_file_lookup = {}
		for workflow_file_json in workflow_files_json:
			workflow_file_lookup[workflow_file_json["id"]] = workflow_file_json

		for workflow_file_link_json in workflow_file_links_json:
			file_id = workflow_file_link_json.get("file_id")
			if file_id is None:
				raise InvalidDeployment(f"no 'file_id' found in workflow file link: {workflow_file_link_json}")

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
		self._workflow_state_lookup.add_state(workflow_state)

	def add_node_to_merge_transition(self, origin_node: WorkflowState, next_node: WorkflowState):
		existing_next_nodes = self._merge_workflow_relationship_lookup.get(next_node.id)
		if existing_next_nodes:
			existing_next_nodes.append(origin_node.id)
		else:
			self._merge_workflow_relationship_lookup[next_node.id] = [origin_node.id]

	def finalize_merge_transitions(self):
		for next_node_id, origin_node_ids in self._merge_workflow_relationship_lookup.items():
			sibiling_list = []
			origin_nodes = []
			for origin_node_id in origin_node_ids:
				origin_node = self._workflow_state_lookup[origin_node_id]
				sibiling_list.append(origin_node.get_state_id())
				origin_nodes.append(origin_node)

			for origin_node in origin_nodes:
				origin_node.set_merge_siblings_for_target(next_node_id, sibiling_list)

	def set_env_vars_for_workflow_state(self, workflow_state: WorkflowState, env_vars: [str]):
		self._workflow_state_env_vars[workflow_state.id] = env_vars

	def lookup_workflow_state(self, node_id) -> WorkflowState:
		ws = self._workflow_state_lookup[node_id]
		if ws is None:
			raise InvalidDeployment(f"Unable to find {node_id} in project")

		return ws

	def lookup_workflow_files(self, node_id) -> List[Dict]:
		files = self._workflow_file_lookup.get(node_id)
		if files is None:
			return []

		return files

	def _cleanup_unused_workflow_state_resources(self, task_spawner):
		cleanup_futures = []
		for workflow_state in self._workflow_state_lookup.states():
			cleanup_futures.append(workflow_state.cleanup(task_spawner, self))

		return cleanup_futures

	def get_predeploy_futures(self):
		predeploy_futures = []

		for workflow_state in self._workflow_state_lookup.states():
			predeploy_futures.append(workflow_state.predeploy(self.task_spawner))

		return predeploy_futures

	@gen.coroutine
	def handle_deploy_futures(self, deploy_futures):
		deployment_exceptions = []

		for deploy_future_data in deploy_futures:
			workflow_state = deploy_future_data["workflow_state"]
			future = deploy_future_data["future"]

			try:
				yield future
				logit(f"Deployed node '{workflow_state.name}' successfully!")

			except Exception as e:
				# guard for not dumping our application stack to the user
				internal_error = True

				logit(f"Failed to deploy node '{workflow_state.name}'!", "error")

				exception_msg = traceback.format_exc()
				if isinstance(e, BuildException):
					# noinspection PyUnresolvedReferences
					exception_msg = e.build_output
					internal_error = False

				logit("Deployment failure exception details: " + repr(exception_msg), "error")
				deployment_exceptions.append(DeploymentException(
					workflow_state.id,
					workflow_state.name,
					workflow_state.type.value,
					internal_error,
					exception_msg
				))

		raise gen.Return(deployment_exceptions)

	def get_workflow_state_future(self, workflow_state: WorkflowState):
		return None

	def get_workflow_state_futures(self):
		deploy_futures = []
		for workflow_state in self._workflow_state_lookup.states():
			deploy_future = self.get_workflow_state_future(workflow_state)

			if deploy_future is None:
				deploy_future = workflow_state.deploy(
					self.task_spawner, self.project_id, self.project_config)

			if deploy_future is None:
				continue

			deploy_futures.append({
				"future": deploy_future,
				"workflow_state": workflow_state
			})

		return deploy_futures

	@gen.coroutine
	def deploy(self):
		"""
		For every workflow state, deployment is broken up into:
		# predeploy
			- Transitions between workflow states are enumerated and created
			- Existence of whether the workflow state is deployed is determined
			- The current state is hashed for later use
		# deploy
			- Current state hashes are compared to their previous state for determining if redeployment is required
			- Future is returned for the deployment of the state, if needed
			- If an exception occurs for the deployment of any state, the entire function will return with all encountered errors
		# update
			- Any states which depend on the deployed state of another state will be appropriately updated
		# cleanup
			- Any states which may have resources to remove post deployment (from a past state) will be removed here

		:return:
		"""
		pass

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

		# Add transition data to each Lambda
		for workflow_relationship_json in diagram_data["workflow_relationships"]:
			workflow_relationship_from_json(self, workflow_relationship_json)
		self.finalize_merge_transitions()
