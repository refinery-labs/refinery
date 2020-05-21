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
	from assistants.task_spawner.task_spawner_assistant import TaskSpawner


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
			"state_hash": self.current_state.state_hash,
		}

	def get_state_hash(self):
		lambda_values = {
			**self.serialize(),
			"execution_pipeline_id": self.execution_pipeline_id,
			"execution_log_level": self.execution_log_level,
			"shared_files_list": self.shared_files_list,
			"role": self.role,

			# override the attributes we want to hold constant
			"name": self.name,
			"arn": ""
		}

		# print(json.dumps(lambda_values, indent=2))

		serialized_lambda_values = json.dumps(lambda_values).encode('utf-8')
		return hashlib.sha256(serialized_lambda_values).hexdigest()

	def get_content_hash(self):
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

	def get_s3_package_hash(self):
		# Generate libraries object for now until we modify it to be a dict/object
		libraries_object = {str(library): "latest" for library in self.libraries}

		is_inline_execution_string = "-INLINE" if self.is_inline_execution else "-NOT_INLINE"

		# Generate SHA256 hash input for caching key
		hash_input = self.language + "-" + self.code + "-" + json.dumps(
			libraries_object,
			sort_keys=True
		) + json.dumps(
			self.shared_files_list
		) + is_inline_execution_string

		return hashlib.sha256(bytes(hash_input, encoding="UTF-8")).hexdigest()

	def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
		super(LambdaWorkflowState, self).setup(deploy_diagram, workflow_state_json)

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

	def _get_transition_env_data(self):
		env_transitions = {
			transition_type.value: [t.serialize() for t in transitions_for_type]
			for transition_type, transitions_for_type in self.transitions.items()
		}
		return json.dumps(env_transitions)

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

	@gen.coroutine
	def update_lambda(self, task_spawner: TaskSpawner):
		updated_lambda_version = yield task_spawner.publish_new_aws_lambda_version(
			self._credentials,
			self
		)

		logit(f"Created a new version for lambda {self.name}, version: {updated_lambda_version}")

	@gen.coroutine
	def predeploy(self, task_spawner):
		logit(f"Preeploy for Lambda '{self.name}'...")

		# finalize the transition data into an environment variable
		self.environment_variables["TRANSITION_DATA"] = self._get_transition_env_data()

		# calculate the current state's hash so we can later on
		# determine if this state has been modified
		# NOTE: aws lambda has their own tracking for this with RevisionId
		# but we choose to use our own hash so that we are not too tightly coupled
		# with their versioning logic
		self.current_state.state_hash = self.get_state_hash()

		if self.deployed_state is not None:
			# check on the deployed state to see if it exists
			exists = yield task_spawner.get_aws_lambda_existence_info(
				self._credentials,
				self
			)
			self.deployed_state.exists = exists

	def deploy(self, task_spawner, project_id, project_config):
		logit(f"Deploying Lambda '{self.name}'...")

		# set this workflow's layers to be the language specific layer in addition
		# to any user supplied layers
		self.layers = get_layers_for_lambda(
			self.language
		) + self.layers

		# if the state has not changed and the lambda exists, then we do not need to do anything
		if not self.state_has_changed() and self.deployed_state_exists():
			logit(f"{self.name} has not changed and is currently deployed, not redeploying")
			return None

		# if the state has changed but the lambda exists, then we can publish a new version of the lambda
		if self.deployed_state_exists():
			logit(f"{self.name} has changed and lambda exists, creating new version")
			return self.update_lambda(task_spawner)

		# lambda does not exist, we must create a new one
		return self.deploy_lambda(task_spawner)
