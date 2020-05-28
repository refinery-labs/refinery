from tornado import gen
from typing import Dict

from assistants.deployments.aws.lambda_function import LambdaWorkflowState
from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
from assistants.deployments.diagram.errors import InvalidDeployment
from assistants.deployments.diagram.queue import QueueWorkflowState
from utils.general import logit


class SqsQueueWorkflowState(QueueWorkflowState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO should we change this name to something random since it takes up to 60 seconds to delete a queue?
        # we are unable to create a queue with the same name on redeploy until the other one has been deleted.
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.delete_queue
        # self.name += random_value

        self.url = ''
        self.batch_size = None
        self.visibility_timeout = 900 # Max Lambda runtime - TODO set this to the linked Lambda amount

    def serialize(self):
        serialized_ws = super(SqsQueueWorkflowState, self).serialize()
        return {
            **serialized_ws,
            "batch_size": self.batch_size
        }

    def setup(self, deploy_diagram: DeploymentDiagram, workflow_state_json: Dict[str, str]):
        super().setup(deploy_diagram, workflow_state_json)

        region = self._credentials["region"]
        account_id = self._credentials["account_id"]

        self.url = f"https://sqs.{region}.amazonaws.com/{account_id}/{self.name}"

        try:
            self.batch_size = int(workflow_state_json["batch_size"])
        except ValueError:
            raise InvalidDeployment(f"unable to parse 'batch_size' for SQS Queue: {self.name}")

    def deploy(self, task_spawner, project_id, project_config):
        logit(f"Deploying SQS queue '{self.name}'...")
        return task_spawner.create_sqs_queue(
            self._credentials,
            self
        )

    @gen.coroutine
    def predeploy(self, task_spawner):
        return task_spawner.get_sqs_existence_info(
            self._credentials,
            self
        )

    def _link_trigger_to_next_deployed_state(self, task_spawner, next_node: LambdaWorkflowState):
        if next_node.deployed_state_exists() and next_node.deployed_state.is_linked_to_trigger(self):
            # We already have this trigger linked to the next node
            return

        return task_spawner.map_sqs_to_lambda(
            self._credentials,
            self,
            next_node,
        )
