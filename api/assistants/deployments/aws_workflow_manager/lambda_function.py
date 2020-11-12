from __future__ import annotations

from tornado import gen
from typing import Dict, TYPE_CHECKING

from assistants.deployments.aws import lambda_function
from assistants.deployments.aws.utils import get_language_specific_environment_variables
from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
from utils.general import logit

if TYPE_CHECKING:
    from assistants.task_spawner.task_spawner_assistant import TaskSpawner
    from assistants.deployments.aws_workflow_manager.aws_deployment import AwsDeployment


class LambdaWorkflowState(lambda_function.LambdaWorkflowState):
    """
    LambdaWorkflowState is an in-memory representation of a lambda object which is created by the user.
    """

    def __init__(self, credentials, _id, name, _type, is_inline_execution=False, **kwargs):
        super().__init__(credentials, _id, name, _type, is_inline_execution=is_inline_execution, **kwargs)

        account_id = str(self._credentials["account_id"])
        account_type = self._credentials["account_type"]
        if account_type == "THIRDPARTY":
            # TODO this role needs to change for the workflow manager
            self.role = f"arn:aws:iam::{account_id}:role/{THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME}"
        else:
            self.role = f"arn:aws:iam::{account_id}:role/refinery_workflow_manager_aws_lambda_role"

        self._workflow_manager_invoke_url = None

    def setup(self, deploy_diagram: AwsDeployment, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)

        self._workflow_manager_invoke_url = deploy_diagram.get_workflow_manager_invoke_url(self.id)

    def _set_environment_variables_for_lambda(self):
        # Add environment variables depending on language
        # This is mainly for module loading when we're doing inline executions.
        language_specific_env_vars = get_language_specific_environment_variables(
            self.language
        )

        self.environment_variables = {
            **language_specific_env_vars,
            **self.environment_variables
        }

    @gen.coroutine
    def predeploy(self, task_spawner: TaskSpawner):
        logit(f"Predeploy for Lambda '{self.name}'...")

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
