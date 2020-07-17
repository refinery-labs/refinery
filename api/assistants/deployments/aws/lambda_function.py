from __future__ import annotations

import hashlib
import json

from tornado import gen
from typing import Dict, List, TYPE_CHECKING

from assistants.deployments.aws.aws_workflow_state import AwsWorkflowState
from assistants.deployments.aws.response_types import LambdaEventSourceMapping
from assistants.deployments.aws.types import AwsDeploymentState
from assistants.deployments.diagram.code_block import CodeBlockWorkflowState
from assistants.deployments.diagram.types import StateTypes
from assistants.deployments.aws.utils import get_language_specific_environment_variables, get_layers_for_lambda
from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
from utils.general import logit
from utils.sym_crypto import encrypt


if TYPE_CHECKING:
    from assistants.task_spawner.task_spawner_assistant import TaskSpawner
    from assistants.deployments.aws.aws_deployment import AwsDeployment


class LambdaDeploymentState(AwsDeploymentState):
    def __init__(self, name, state_type, state_hash, arn):
        super().__init__(name, state_type, state_hash, arn)

        self.event_source_mappings: List[LambdaEventSourceMapping] = []

    def __str__(self):
        return f'Lambda Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}, event_source_mappings: {self.event_source_mappings}'

    def is_linked_to_trigger(self, trigger_state: AwsWorkflowState):
        return any([mapping.event_source_arn == trigger_state.arn for mapping in self.event_source_mappings])


class LambdaWorkflowState(AwsWorkflowState, CodeBlockWorkflowState):
    """
    LambdaWorkflowState is an in-memory representation of a lambda object which is created by the user.
    """

    def __init__(self, credentials, _id, name, _type, user_tier, pidgeon_key, is_inline_execution=False, **kwargs):
        super().__init__(credentials, _id, name, _type, **kwargs)

        self.is_inline_execution = is_inline_execution
        self.max_execution_time = None
        self.memory = None
        self.execution_pipeline_id = None
        self.execution_log_level = None
        self.reserved_concurrency_count = False
        self.user_tier = user_tier
        self.pidgeon_key = pidgeon_key

        self.execution_mode = "REGULAR"
        self.tags_dict = {
            "RefineryResource": "true"
        }

        # If it's a self-hosted (THIRDPARTY) AWS account we deploy with a different role
        # name which they manage themselves.
        account_id = str(self._credentials["account_id"])
        account_type = self._credentials["account_type"]
        if account_type == "THIRDPARTY":
            self.role = f"arn:aws:iam::{account_id}:role/{THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME}"
        else:
            self.role = f"arn:aws:iam::{account_id}:role/refinery_default_aws_lambda_role"

        self.deployed_state: LambdaDeploymentState = self.deployed_state

    def setup(self, deploy_diagram: AwsDeployment, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)

        if self.deployed_state is None:
            self.deployed_state = LambdaDeploymentState(self.name, self.type, None, arn=self.arn)

        # set this workflow's layers to be the language specific layer in addition
        # to any user supplied layers
        self.layers = get_layers_for_lambda(
            self.language
        ) + self.layers

        self.execution_pipeline_id = deploy_diagram.project_id
        self.execution_log_level = deploy_diagram.project_config["logging"]["level"]

        self.memory = workflow_state_json.get("memory")
        self.max_execution_time = workflow_state_json.get("max_execution_time")

        if "reserved_concurrency_count" in workflow_state_json:
            self.reserved_concurrency_count = workflow_state_json["reserved_concurrency_count"]

        self._set_environment_variables_for_lambda()

    def serialize(self) -> Dict[str, str]:
        base_ws_state = super().serialize()
        return {
            **base_ws_state,
            "max_execution_time": self.max_execution_time,
            "memory": self.memory,
            "reserved_concurrency_count": self.reserved_concurrency_count
        }

    def get_state_hash(self):
        lambda_values = {
            **self.serialize(),
            "execution_pipeline_id": self.execution_pipeline_id,
            "execution_log_level": self.execution_log_level,
            "shared_files_list": self.shared_files_list,
            "role": self.role
        }

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

    def _set_environment_variables_for_lambda(self):
        # Add environment variables depending on language
        # This is mainly for module loading when we're doing inline executions.
        language_specific_env_vars = get_language_specific_environment_variables(
            self.language
        )

        all_environment_vars = {
           # Deployment id
            "EXECUTION_PIPELINE_ID": self.execution_pipeline_id,
            "LOG_BUCKET_NAME": self._credentials["logs_bucket"],
            "PACKAGES_BUCKET_NAME": self._credentials["lambda_packages_bucket"],
            "PIPELINE_LOGGING_LEVEL": self.execution_log_level,
            "EXECUTION_MODE": self.execution_mode,
            **language_specific_env_vars,
            **self.environment_variables
        }

        if self._uses_pidgeon():
            all_environment_vars.update({
                "PIDGEON_URL": self._get_pidgeon_url(),
                "PIDGEON_AUTH": self._get_pidgeon_auth(self.execution_pipeline_id)
            })
        else:
            all_environment_vars.update({
                "REDIS_HOSTNAME": self._credentials["redis_hostname"],
                "REDIS_PASSWORD": self._credentials["redis_password"],
                "REDIS_PORT": str(self._credentials["redis_port"])
            })

        if self.is_inline_execution:
            # The environment variable activates it as
            # an inline execution Lambda and allows us to
            # pass in arbitrary code to execution.
            all_environment_vars["IS_INLINE_EXECUTOR"] = "True"

        self.environment_variables = all_environment_vars

    def _uses_pidgeon(self):
        # TODO user constants
        return self.user_tier == "free"

    def _get_pidgeon_url(self):
        return ""

    def _get_pidgeon_auth(self, deployment_id):
        return encrypt(self.pidgeon_key, {"deployment_id": deployment_id})

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

        deployed_arn = deployed_lambda_data["FunctionArn"]
        self.set_arn(deployed_arn)

        # If we have concurrency set, then we'll set that for our deployed Lambda
        if self.reserved_concurrency_count:
            logit(f"Setting reserved concurrency for Lambda '{deployed_arn}' to {self.reserved_concurrency_count}...")
            yield task_spawner.set_lambda_reserved_concurrency(
                self._credentials,
                deployed_arn,
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
    def predeploy(self, task_spawner: TaskSpawner):
        logit(f"Predeploy for Lambda '{self.name}'...")

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

        # Enumerate the event source mappings for this lambda
        if self.deployed_state_exists():
            self.deployed_state.event_source_mappings = yield task_spawner.list_lambda_event_source_mappings(
                self._credentials,
                self
            )

    def deploy(self, task_spawner, project_id, project_config):
        logit(f"Deploying Lambda '{self.name}'...")

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

    @gen.coroutine
    def cleanup(self, task_spawner: TaskSpawner, deployment: AwsDeployment):
        if not self.deployed_state_exists():
            raise gen.Return()

        # Remove any event source mappings created by sqs queues that do not exist anymore
        for mapping in self.deployed_state.event_source_mappings:
            queue_uuid = mapping.uuid
            queue_arn = mapping.event_source_arn

            # TODO can we guarantee that this will be a sqs queue?
            exists = deployment.validate_arn_exists_and_mark_for_cleanup(StateTypes.SQS_QUEUE, queue_arn)
            if not exists:
                task_spawner.delete_lambda_event_source_mapping(
                    self._credentials,
                    queue_uuid
                )
