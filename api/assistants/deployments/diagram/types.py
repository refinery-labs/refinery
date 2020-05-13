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
