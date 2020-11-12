from __future__ import annotations

import uuid

from tornado import gen
from typing import Dict, TYPE_CHECKING

from assistants.deployments.aws import sqs_queue
from assistants.deployments.aws_workflow_manager.lambda_function import LambdaWorkflowState
from assistants.deployments.aws_workflow_manager.sqs_queue_handler import SqsQueueHandlerWorkflowState
from assistants.deployments.diagram.types import StateTypes
from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from utils.general import logit

if TYPE_CHECKING:
    from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram


class SqsQueueWorkflowState(sqs_queue.SqsQueueWorkflowState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._queue_handler: LambdaWorkflowState = None
        self._workflow_manager_invoke_url = None

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, str]):
        super().setup(deploy_diagram, workflow_state_json)

        self._workflow_manager_invoke_url = deploy_diagram.get_workflow_manager_invoke_url(self.id)

        self._queue_handler = SqsQueueHandlerWorkflowState(
            self._credentials,
            str(uuid.uuid4()),
            "queue_handler_" + self.id,
            StateTypes.SQS_QUEUE_HANDLER
        )
        deploy_diagram.add_workflow_state(self._queue_handler)

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

    def _link_trigger_to_next_deployed_state(self, task_spawner: TaskSpawner, next_node: LambdaWorkflowState):
        pass
