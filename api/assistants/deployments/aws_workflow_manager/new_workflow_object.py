from __future__ import annotations

from typing import Dict, TYPE_CHECKING, Union, Type

from assistants.deployments.aws.api_gateway import ApiGatewayResponseWorkflowState
from assistants.deployments.aws.new_workflow_object import do_workflow_state_from_json
from assistants.deployments.aws_workflow_manager.api_endpoint import ApiEndpointWorkflowState
from assistants.deployments.aws_workflow_manager.cloudwatch_rule import ScheduleTriggerWorkflowState
from assistants.deployments.aws_workflow_manager.lambda_function import LambdaWorkflowState
from assistants.deployments.aws_workflow_manager.sns_topic import SnsTopicWorkflowState
from assistants.deployments.aws_workflow_manager.sqs_queue import SqsQueueWorkflowState
from assistants.deployments.diagram.types import StateTypes


if TYPE_CHECKING:
	from assistants.deployments.diagram.workflow_states import WorkflowState
	from assistants.deployments.aws_workflow_manager.aws_deployment import AwsDeployment

	WorkflowStateTypes = Type[Union[
		LambdaWorkflowState, ApiEndpointWorkflowState, SqsQueueWorkflowState,
		SnsTopicWorkflowState, ScheduleTriggerWorkflowState
	]]


def workflow_state_from_json(credentials, deploy_diagram: AwsDeployment, workflow_state_json: Dict) -> WorkflowState:
	state_type_to_workflow_state: Dict[StateTypes, WorkflowStateTypes] = {
		StateTypes.LAMBDA: LambdaWorkflowState,
		StateTypes.API_ENDPOINT: ApiEndpointWorkflowState,
		StateTypes.SQS_QUEUE: SqsQueueWorkflowState,
		StateTypes.SNS_TOPIC: SnsTopicWorkflowState,
		StateTypes.SCHEDULE_TRIGGER: ScheduleTriggerWorkflowState,
		StateTypes.API_GATEWAY_RESPONSE: ApiGatewayResponseWorkflowState
	}
	return do_workflow_state_from_json(
		state_type_to_workflow_state,
		credentials,
		deploy_diagram,
		workflow_state_json
	)
