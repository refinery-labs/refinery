from __future__ import annotations

import uuid

from tornado import gen
from typing import Dict, TYPE_CHECKING

from assistants.deployments.aws_workflow_manager.aws_workflow_state import AwsWorkflowState
from assistants.deployments.aws_workflow_manager.lambda_function import LambdaWorkflowState
from assistants.deployments.aws_workflow_manager.sqs_queue_handler import SqsQueueHandlerWorkflowState
from assistants.deployments.aws_workflow_manager.types import AwsDeploymentState
from assistants.deployments.diagram.errors import InvalidDeployment
from assistants.deployments.diagram.queue import QueueWorkflowState
from assistants.deployments.diagram.types import StateTypes
from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from utils.general import logit

if TYPE_CHECKING:
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


class SqsQueueWorkflowState(AwsWorkflowState, QueueWorkflowState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO should we change this name to something random since it takes up to 60 seconds to delete a queue?
        # we are unable to create a queue with the same name on redeploy until the other one has been deleted.
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.delete_queue
        # self.name += random_value

        self.url = ''
        self.batch_size = None
        self.visibility_timeout = 900 # Max Lambda runtime - TODO set this to the linked Lambda amount

        self._queue_handler: LambdaWorkflowState = None

    def serialize(self):
        serialized_ws = super().serialize()
        return {
            **serialized_ws,
            "url": self.url,
            "batch_size": self.batch_size
        }

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, str]):
        super().setup(deploy_diagram, workflow_state_json)

        if self.deployed_state is None:
            self.deployed_state = AwsDeploymentState(self.name, StateTypes.SQS_QUEUE, None, self.arn)

        region = self._credentials["region"]
        account_id = self._credentials["account_id"]

        self.url = f"https://sqs.{region}.amazonaws.com/{account_id}/{self.name}"

        self._workflow_manager_invoke_url = deploy_diagram.get_workflow_manager_invoke_url(self.id)

        self._queue_handler = SqsQueueHandlerWorkflowState(
            self._credentials,
            str(uuid.uuid4()),
            "queue_handler_" + self.id,
            StateTypes.SQS_QUEUE_HANDLER
        )
        deploy_diagram.add_workflow_state(self._queue_handler)

        try:
            self.batch_size = int(workflow_state_json["batch_size"])
        except ValueError:
            raise InvalidDeployment(f"unable to parse 'batch_size' for SQS Queue: {self.name}")

    @gen.coroutine
    def deploy_and_link_sqs_queue(self, task_spawner):
        resp = yield task_spawner.deploy_aws_lambda_with_code(
            self._credentials,
            self._queue_handler,
            self._workflow_manager_invoke_url
        )
        deployed_arn = resp["FunctionArn"]
        self._queue_handler.set_arn(deployed_arn)

        task_spawner.create_cloudwatch_group(
            self._credentials,
            f"/aws/lambda/{self._queue_handler.name}",
            {
                "RefineryResource": "true"
            },
            7
        )

        yield task_spawner.create_sqs_queue(
            self._credentials,
            self
        )
        yield task_spawner.map_sqs_to_lambda(
            self._credentials,
            self,
            self._queue_handler
        )

    def deploy(self, task_spawner, project_id, project_config):
        logit(f"Deploying SQS queue '{self.name}'...")
        return self.deploy_and_link_sqs_queue(task_spawner)

    @gen.coroutine
    def predeploy(self, task_spawner):
        self.deployed_state.exists = task_spawner.get_sqs_existence_info(
            self._credentials,
            self
        )

    def _link_trigger_to_next_deployed_state(self, task_spawner: TaskSpawner, next_node: LambdaWorkflowState):
        pass
