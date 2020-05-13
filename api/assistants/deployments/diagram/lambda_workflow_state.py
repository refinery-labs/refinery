from __future__ import annotations

import hashlib
import json

from tornado import gen
from typing import Dict, List, TYPE_CHECKING

from assistants.deployments.diagram.utils import get_language_specific_environment_variables, get_layers_for_lambda
from assistants.deployments.diagram.workflow_states import WorkflowState
from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
from utils.general import logit

if TYPE_CHECKING:
	from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


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
		self.tags_dict = {
			"RefineryResource": "true"
		}
		self.environment_variables = {}
		self.shared_files_list: List = []

		# If it's a self-hosted (THIRDPARTY) AWS account we deploy with a different role
		# name which they manage themselves.
		if credentials["account_type"] == "THIRDPARTY":
			self.role = "arn:aws:iam::" + str(credentials["account_id"]) + ":role/" + THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
		else:
			self.role = "arn:aws:iam::" + str(credentials["account_id"]) + ":role/refinery_default_aws_lambda_role"

		# Save the original name the user made for this lambda
		self._original_name = self.name
		self._previous_deploy_hash = None
		self._current_deploy_hash = None

	def hash(self):
		lambda_values = {
			**self.serialize(),
			"execution_pipeline_id": self.execution_pipeline_id,
			"execution_log_level": self.execution_log_level,
			"shared_files_list": self.shared_files_list,
			"role": self.role,
			"name": self._original_name
		}
		serialized_lambda_values = json.dumps(lambda_values).encode('utf-8')
		self._current_deploy_hash = hashlib.sha256(serialized_lambda_values).hexdigest()

	def serialize(self) -> Dict[str, str]:
		base_ws_state = super(LambdaWorkflowState, self).serialize()
		return {
			**base_ws_state,
			"language": self.language,
			"code": self.code,
			"max_execution_time": self.max_execution_time,
			"memory": self.memory,
			"reserved_concurrency_count": self.reserved_concurrency_count,
			"layers": self.layers,
			"libraries": self.libraries,
			"environment_variables": self.environment_variables,
			"hash": self._current_deploy_hash
		}

	def get_hash_key(self):
		"""
		Used by the Code Runner to determine if there is a lambda already deployed
		that can be reused.

		:return: hash of lambda for inline executions
		"""
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

		return hashlib.sha256(
			json.dumps(
				hash_dict,
				sort_keys=True
			).encode('utf-8')
		).hexdigest()

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		self.execution_pipeline_id = deploy_diagram.project_id
		self.execution_log_level = deploy_diagram.project_config["logging"]["level"]

		if self.is_inline_execution:
			env_vars = {
				env_var["key"]: env_var["value"]
				for env_var in workflow_state_json["environment_variables"]
			}
			self._set_environment_variables_for_lambda(env_vars)
		else:
			env_vars = self._get_project_env_vars(deploy_diagram, workflow_state_json)
			self._set_environment_variables_for_lambda(env_vars)

		if "shared_files" in workflow_state_json:
			self.shared_files_list = workflow_state_json["shared_files"]

		self.shared_files_list.extend(deploy_diagram.lookup_workflow_files(self.id))

		self.language = workflow_state_json["language"]
		self.code = workflow_state_json["code"]
		self.libraries = workflow_state_json["libraries"]
		self.max_execution_time = workflow_state_json["max_execution_time"]
		self.memory = workflow_state_json["memory"]
		self.layers = workflow_state_json["layers"]

		if "reserved_concurrency_count" in workflow_state_json:
			self.reserved_concurrency_count = workflow_state_json["reserved_concurrency_count"]

		self.set_name(self.name + deploy_diagram.get_unique_workflow_state_name())

		self._previous_deploy_hash = deploy_diagram.get_previous_state(self.id)

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
			arn = deployed_lambda_data["FunctionArn"]
			logit(f"Setting reserved concurrency for Lambda '{arn}' to {self.reserved_concurrency_count}...")
			yield task_spawner.set_lambda_reserved_concurrency(
				self._credentials,
				arn,
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

		self.hash()

		print(self._current_deploy_hash, self._previous_deploy_hash)

		# TODO we could probably clean up this interface
		return self.deploy_lambda(task_spawner)
