from typing import Union, Dict, List

from assistants.deployments.aws.aws_deployment import AwsDeployment
from assistants.deployments.aws.aws_workflow_relationships import AwsWorkflowRelationship
from assistants.deployments.aws.types import AwsDeploymentState
from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
from assistants.deployments.diagram.types import StateTypes, RelationshipTypes
from assistants.deployments.diagram.workflow_relationship import MergeWorkflowRelationship
from assistants.deployments.diagram.workflow_states import WorkflowState


class AwsWorkflowState(WorkflowState):
    def __init__(self, *args, arn=None, force_redeploy=False, **kwargs):
        super().__init__(*args, **kwargs)

        arn = self.get_arn_name() if arn is None else arn
        self.deployed_state: Union[AwsDeploymentState, None] = None

        self.transitions: Dict[RelationshipTypes, List[AwsWorkflowRelationship]] = self.transitions

        self.current_state: AwsDeploymentState = AwsDeploymentState(self.type, None, arn=arn)

        self.force_redeploy = force_redeploy

    def setup(self, deploy_diagram: AwsDeployment, workflow_state_json: Dict[str, object]):
        super().setup(deploy_diagram, workflow_state_json)

        self.deployed_state = deploy_diagram.get_previous_state(self.id)

    def serialize(self):
        ws_serialized = super().serialize()
        return {
            **ws_serialized,
            "transitions": {
                transition_type.value: [t.serialize() for t in transitions_for_type]
                for transition_type, transitions_for_type in self.transitions.items()
            },
            "arn": self.arn
        }

    def get_state_id(self):
        return self.arn

    @property
    def arn(self):
        return self.current_state.arn

    def set_arn(self, arn):
        self.current_state.arn = arn

    def get_arn_name(self):
        name_prefix = ''
        if self.type == StateTypes.LAMBDA or self.type == StateTypes.API_ENDPOINT:
            arn_type = 'lambda'
            name_prefix = 'function:'
        elif self.type == StateTypes.SNS_TOPIC:
            arn_type = 'sns'
        elif self.type == StateTypes.SQS_QUEUE:
            arn_type = 'sqs'
        elif self.type == StateTypes.SCHEDULE_TRIGGER:
            arn_type = 'events'
            name_prefix = 'rule/'
        else:
            # For pseudo-nodes like API Responses we don't need to create a teardown entry
            return None

        region = self._credentials["region"]
        account_id = self._credentials["account_id"]

        # Set ARN on workflow state
        return f'arn:aws:{arn_type}:{region}:{account_id}:{name_prefix}{self.name}'

    def state_has_changed(self) -> bool:
        assert self.current_state is not None

        if self.force_redeploy:
            return True

        if self.deployed_state is None:
            return True
        return self.deployed_state.state_changed(self.current_state)

    def deployed_state_exists(self) -> bool:
        if self.deployed_state is None:
            return False
        return self.deployed_state.exists

    def set_name(self, name):
        self.name = name
        self.current_state.arn = self.get_arn_name()
