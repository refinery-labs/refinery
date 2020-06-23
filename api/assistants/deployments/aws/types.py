from typing import Union

from assistants.deployments.diagram.types import DeploymentState, StateTypes


class AwsDeploymentState(DeploymentState):
    def __init__(self, name, state_type: StateTypes, state_hash, arn):
        super().__init__(name, state_type, state_hash)
        self.arn: str = arn

    @property
    def id(self):
        return self.arn
