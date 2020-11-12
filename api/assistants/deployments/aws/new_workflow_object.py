from __future__ import annotations

from typing import Dict, TYPE_CHECKING, Union, Type

from assistants.deployments.aws.api_endpoint import ApiEndpointWorkflowState
from assistants.deployments.aws.api_gateway import ApiGatewayResponseWorkflowState
from assistants.deployments.aws.cloudwatch_rule import ScheduleTriggerWorkflowState
from assistants.deployments.aws.lambda_function import LambdaWorkflowState
from assistants.deployments.aws.sns_topic import SnsTopicWorkflowState
from assistants.deployments.aws.sqs_queue import SqsQueueWorkflowState
from assistants.deployments.diagram.errors import InvalidDeployment
from assistants.deployments.diagram.types import StateTypes, RelationshipTypes


if TYPE_CHECKING:
	from assistants.deployments.diagram.workflow_states import WorkflowState
	from assistants.deployments.aws.aws_deployment import AwsDeployment

	WorkflowStateTypes = Type[Union[
		LambdaWorkflowState, ApiEndpointWorkflowState, SqsQueueWorkflowState,
		SnsTopicWorkflowState, ScheduleTriggerWorkflowState
	]]


def do_workflow_state_from_json(
	state_type_to_workflow_state: Dict[StateTypes, WorkflowStateTypes],
	credentials,
	deploy_diagram: AwsDeployment,
	workflow_state_json: Dict
) -> WorkflowState:
	node_id = workflow_state_json["id"]
	node_type = workflow_state_json["type"]

	try:
		state_type = StateTypes(workflow_state_json["type"])
	except ValueError as e:
		raise InvalidDeployment(f"workflow state {node_id} has invalid type {node_type}")

	workflow_state_type = state_type_to_workflow_state.get(state_type)

	if workflow_state_json is None:
		raise InvalidDeployment(f"invalid workflow state type: {state_type} for workflow state: {node_id}")

	workflow_state = workflow_state_type(
		credentials,
		workflow_state_json.get("id"),
		workflow_state_json.get("name"),
		state_type
	)

	workflow_state.setup(deploy_diagram, workflow_state_json)

	return workflow_state


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


def workflow_relationship_from_json(deploy_diagram: AwsDeployment, workflow_relationship_json: Dict):
	try:
		relation_type = RelationshipTypes(workflow_relationship_json["type"])
	except ValueError as e:
		relation_id = workflow_relationship_json["id"]
		relation_type = workflow_relationship_json["type"]
		raise InvalidDeployment(f"workflow relationship {relation_id} has invalid type {relation_type}")

	origin_node_id = workflow_relationship_json["node"]
	next_node_id = workflow_relationship_json["next"]

	origin_node = deploy_diagram.lookup_workflow_state(origin_node_id)
	next_node = deploy_diagram.lookup_workflow_state(next_node_id)

	origin_node.create_transition(
		deploy_diagram, relation_type, next_node, workflow_relationship_json)
