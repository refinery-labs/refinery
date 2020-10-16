from __future__ import annotations

from tornado import gen
from typing import Dict, List, TYPE_CHECKING

from assistants.deployments.aws_workflow_manager.aws_workflow_state import AwsWorkflowState
from assistants.deployments.aws_workflow_manager.response_types import TopicSubscription
from assistants.deployments.aws_workflow_manager.types import AwsDeploymentState
from assistants.deployments.diagram.topic import TopicWorkflowState
from assistants.deployments.diagram.types import StateTypes
from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from utils.general import logit

if TYPE_CHECKING:
    from assistants.deployments.aws_workflow_manager.aws_deployment import AwsDeployment
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


class SnsTopicDeploymentState(AwsDeploymentState):
    def __init__(self, name, state_type, state_hash, arn):
        super().__init__(name, state_type, state_hash, arn)

        self.subscriptions: List[TopicSubscription] = []

    def __str__(self):
        return f'Sns Topic Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}, subscriptions: {self.subscriptions}'


class SnsTopicWorkflowState(AwsWorkflowState, TopicWorkflowState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._deployment_id = None

        self.deployed_state: SnsTopicDeploymentState = self.deployed_state

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)
        if self.deployed_state is None:
            self.deployed_state = SnsTopicDeploymentState(self.name, self.type, None, self.arn)

        self._deployment_id = deploy_diagram.deployment_id

    @gen.coroutine
    def _do_deploy(self, task_spawner):
        yield task_spawner.create_sns_topic(
            self._credentials,
            self.id,
            self.name
        )

        workflow_manager_invoke_url = f"https://5nz8oicvrl.execute-api.us-west-2.amazonaws.com/refinery/replaceme/coffeeyakhorn?deploymentID={self._deployment_id}&workflowID={self.id}"
        yield task_spawner.subscribe_workflow_to_sns_topic(
            self._credentials,
            self,
            workflow_manager_invoke_url
        )

    def deploy(self, task_spawner, project_id, project_config):
        logit(f"Deploying SNS topic '{self.name}'...")
        return self._do_deploy(task_spawner)

    @gen.coroutine
    def predeploy(self, task_spawner: TaskSpawner):
        sns_subs_info = yield task_spawner.get_sns_topic_subscriptions(
            self._credentials,
            self
        )

        self.deployed_state.exists = sns_subs_info["exists"]
        self.deployed_state.subscriptions = sns_subs_info["subscriptions"]

    @gen.coroutine
    def cleanup(self, task_spawner: TaskSpawner, deployment: AwsDeployment):
        for subscription in self.deployed_state.subscriptions:
            sub_arn = subscription.subscription_arn
            endpoint = subscription.endpoint

            if subscription.subscription_arn == "PendingConfirmation":
                # TODO figure out how to clean this up properly
                # We can't clean this subscription up since it doesn't have an ARN yet :/
                pass

            exists = deployment.validate_arn_exists_and_mark_for_cleanup(StateTypes.LAMBDA, endpoint)
            if not exists:
                yield task_spawner.unsubscribe_workflow_from_sns_topic(
                    self._credentials,
                    sub_arn
                )

    def _link_trigger_to_next_deployed_state(self, task_spawner, next_node):
        return None
