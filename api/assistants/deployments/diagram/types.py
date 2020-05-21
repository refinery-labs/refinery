from __future__ import annotations

from enum import Enum


class StateTypes(Enum):
	INVALID = "invalid"
	LAMBDA = "lambda"
	SQS_QUEUE = "sqs_queue"
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
	def __init__(self, arn=None, state_hash=None):
		self.arn = arn

		self.state_hash = state_hash

		self.exists = False

	def __str__(self):
		return f'Deployment State arn: {self.arn}, state_hash: {self.state_hash}, exists: {self.exists}'

	def state_changed(self, current_state: DeploymentState):
		return self.state_hash != current_state.state_hash
