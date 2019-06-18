import { ElementDefinition, ElementsDefinition, Stylesheet } from 'cytoscape';
import { HTTP_METHOD } from '@/constants/api-constants';

export interface BaseRefineryResource {
  name: string;
  id: string;
}

export interface RefineryProject {
  name: string;
  project_id: string;
  version: number;
  workflow_states: WorkflowState[];
  workflow_relationships: WorkflowRelationship[];
}

export enum SupportedLanguage {
  PYTHON_2 = 'python2.7',
  NODEJS_8 = 'nodejs8.10',
  PHP7 = 'php7.3',
  GO1_12 = 'go1.12'
}

export enum WorkflowStateType {
  LAMBDA = 'lambda',
  API_GATEWAY_RESPONSE = 'api_gateway_response',
  // TODO: What is this?
  API_GATEWAY = 'api_gateway',
  API_ENDPOINT = 'api_endpoint',
  SNS_TOPIC = 'sns_topic',
  SQS_QUEUE = 'sqs_queue',
  SCHEDULE_TRIGGER = 'schedule_trigger'
}

export enum WorkflowRelationshipType {
  THEN = 'then',
  IF = 'if',
  FAN_OUT = 'fan-out',
  FAN_IN = 'fan-in',
  EXCEPTION = 'exception',
  ELSE = 'else'
}

export enum ProjectLogLevel {
  LOG_ALL = 'LOG_ALL',
  LOG_ERRORS = 'LOG_ERRORS',
  LOG_NONE = 'LOG_NONE'
}

export interface WorkflowState extends BaseRefineryResource {
  type: WorkflowStateType;
}

export interface LambdaWorkflowState extends WorkflowState {
  layers: string[];
  code: string;
  language: SupportedLanguage;
  libraries: string[];
  memory: number;
  max_execution_time: number;
}

export interface ApiEndpointWorkflowState extends WorkflowState {
  api_path: string;
  http_method: HTTP_METHOD;
}

export interface ApiGatewayResponseWorkflowState extends WorkflowState {}

export interface SnsTopicWorkflowState extends WorkflowState {}

export interface SqsQueueWorkflowState extends WorkflowState {
  batch_size: number;
}

export interface ScheduleTriggerWorkflowState extends WorkflowState {
  schedule_expression: string;
  description: string;
  input_string: string;
}

export interface WorkflowRelationship extends BaseRefineryResource {
  node: string;
  type: WorkflowRelationshipType;
  next: string;
  expression: string;
}

export interface ProjectConfig {
  environment_variables: ProjectEnvironmentVariableConfig;
  api_gateway: { gateway_id: string };
  version: string;
  logging: { level: ProjectLogLevel };
}

export interface ProjectEnvironmentVariableConfig {
  [key: string]: ProjectEnvironmentVariable[];
}

export interface ProjectEnvironmentVariable {
  key: string;
  value: string;
}

export type CyElements = ElementsDefinition;

// Let's just not support promises in our API style. If we need it we'll figure it out
export type CyStyle = Stylesheet[]; // | Promise<Stylesheet[]>;
