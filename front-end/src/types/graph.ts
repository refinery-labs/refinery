import {ElementDefinition, ElementsDefinition, Stylesheet} from 'cytoscape';

export interface BaseRefineryResource {
  name: string,
  id: string,
}

export interface RefineryProject extends BaseRefineryResource {
  version: number,
  workflow_states: WorkflowState[],
  workflow_relationships: WorkflowRelationship[]
}

export enum SupportedLanguages {
  PYTHON_2 = "python2.7",
  NODEJS_8 = "nodejs8.10"
}

export enum WorkflowStateType {
  LAMBDA = "lambda",
  API_GATEWAY_RESPONSE = "api_gateway_response",
  API_ENDPOINT = "api_endpoint",
  SNS_TOPIC = "sns_topic",
  SQS_QUEUE = "sqs_queue",
  SCHEDULE_TRIGGER = "schedule_trigger"
}

export enum API_ENDPOINT_HTTP_METHOD {
  GET = "GET",
  POST = "POST",
  PUT = "PUT",
  DELETE = "DELETE"
}

export interface WorkflowState extends BaseRefineryResource {
  type: WorkflowStateType
}

export interface LambdaWorkflowState extends WorkflowState {
  layers: string[],
  code: string,
  language: SupportedLanguages,
  libraries: string[],
  memory: number,
  max_execution_time: number
}

export interface ApiEndpointWorkflowState extends WorkflowState {
  api_path: string,
  http_method: API_ENDPOINT_HTTP_METHOD
}

export interface ApiGatewayResponseWorkflowState extends WorkflowState {}

export interface SnsTopicWorkflowState extends WorkflowState {
  topic_name: string
}

export interface SqsQueueWorkflow extends WorkflowState {
  queue_name: string,
  content_based_deduplication: boolean,
  batch_size: number
}

export interface ScheduleTriggerWorkflowState extends WorkflowState {
  schedule_expression: string,
  description: string,
  unformatted_input_data: string,
  input_dict: {[key: string]: {} | string}
}

export enum WorkflowRelationshipType {
  THEN = "then",
  IF = "if"
}

export interface WorkflowRelationship extends BaseRefineryResource {
  node: string,
  type: WorkflowRelationshipType,
  next: string,
  expression: string
}

export type CyElements = ElementsDefinition | ElementDefinition[] | Promise<ElementsDefinition> | Promise<ElementDefinition[]>;

// Let's just not support promises in our API style. If we need it we'll figure it out
export type CyStyle = Stylesheet[]; // | Promise<Stylesheet[]>;
