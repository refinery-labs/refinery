from typing import Union

from assistants.deployments.diagram.types import DeploymentState, StateTypes


class AwsDeploymentState(DeploymentState):
    def __init__(self, state_type: StateTypes, state_hash: Union[str, None], arn: str):
        super().__init__(state_type, state_hash)
        self.arn: str = arn

    @property
    def id(self):
        return self.arn
