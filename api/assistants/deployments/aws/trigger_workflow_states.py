from __future__ import annotations

import hashlib
import json

from tornado import gen
from typing import Dict, TYPE_CHECKING

from assistants.deployments.diagram.deploy_diagram import InvalidDeployment
from assistants.deployments.diagram.types import StateTypes, SnsTopicDeploymentState, ScheduleTriggerDeploymentState
from assistants.deployments.diagram.workflow_states import WorkflowState
from utils.general import logit

if TYPE_CHECKING:
	from assistants.deployments.diagram.deploy_diagram import DeploymentDiagram
	from assistants.task_spawner.task_spawner_assistant import TaskSpawner
	from assistants.deployments.aws.lambda_workflow_state import LambdaWorkflowState


class WarmerTriggerWorkflowState(WorkflowState):
	pass


