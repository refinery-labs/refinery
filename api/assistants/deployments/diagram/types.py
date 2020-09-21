from __future__ import annotations

from enum import Enum

from typing import Union


class StateTypes(Enum):
	INVALID = "invalid"
	LAMBDA = "lambda"
	SQS_QUEUE = "sqs_queue"
	SQS_QUEUE_HANDLER = "sqs_queue_handler"
	SNS_TOPIC = "sns_topic"
	SCHEDULE_TRIGGER = "schedule_trigger"
	API_ENDPOINT = "api_endpoint"
	API_GATEWAY_RESPONSE = "api_gateway_response"
	API_GATEWAY = "api_gateway"
	WARMER_TRIGGER = "warmer_trigger"


class RelationshipTypes(Enum):
	IF = "if"
	ELSE = "else"
	EXCEPTION = "exception"
	THEN = "then"
	FAN_OUT = "fan-out"
	FAN_IN = "fan-in"
	MERGE = "merge"


class DeploymentState:
	def __init__(self, name, state_type: StateTypes, state_hash: Union[str, None]):
		self.name = name
		self.type: StateTypes = state_type
		self.state_hash: Union[str, None] = state_hash

		self.exists: bool = False

	def __str__(self):
		return f'Deployment State state_hash: {self.state_hash}, exists: {self.exists}'

	def state_changed(self, current_state: DeploymentState):
		return self.state_hash != current_state.state_hash
