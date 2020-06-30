import { HTTP_METHOD } from '@/constants/api-constants';
import { DemoTooltip, TooltipType } from '@/types/demo-walkthrough-types';

export interface BaseRefineryResource {
  name: string;
  id: string;
  version: string;
}

export interface RefineryProject {
  name: string;
  project_id: string;
  readme: string;
  version: number;
  workflow_states: WorkflowState[];
  workflow_relationships: WorkflowRelationship[];
  workflow_files: WorkflowFile[];
  workflow_file_links: WorkflowFileLink[];
  global_handlers: GlobalHandlers;
  demo_walkthrough?: DemoTooltip[];
}

export enum SupportedLanguage {
  RUBY2_6_4 = 'ruby2.6.4',
  PYTHON_3 = 'python3.6',
  PYTHON_2 = 'python2.7',
  NODEJS_8 = 'nodejs8.10',
  NODEJS_10 = 'nodejs10.16.3',
  NODEJS_1020 = 'nodejs10.20.1',
  PHP7 = 'php7.3',
  GO1_12 = 'go1.12'
}

export enum WorkflowStateType {
  LAMBDA = 'lambda',
  API_GATEWAY_RESPONSE = 'api_gateway_response',
  // TODO: What is this?
  API_GATEWAY = 'api_gateway',
  WARMER_TRIGGER = 'warmer_trigger',
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
  ELSE = 'else',
  MERGE = 'merge'
}

export enum WorkflowFileType {
  SHARED_FILE = 'shared_file'
}

export interface WorkflowFile extends BaseRefineryResource {
  type: WorkflowFileType;
  body: string;
}

export enum WorkflowFileLinkType {
  SHARED_FILE_LINK = 'shared_file_link'
}

export interface WorkflowFileLink {
  id: string;
  file_id: string;
  node: string;
  version: string;
  type: WorkflowFileLinkType;
  path: string;
}

export enum ProjectLogLevel {
  LOG_ALL = 'LOG_ALL',
  LOG_ERRORS = 'LOG_ERRORS',
  LOG_NONE = 'LOG_NONE'
}

export interface WorkflowState extends BaseRefineryResource {
  type: WorkflowStateType;
  saved_block_metadata?: SavedBlockMetadata;
  tooltip?: DemoTooltip | false;
}

export interface SavedBlockMetadata {
  id: string;
  version: number;
  timestamp: number;
  added_timestamp: number;
}

export interface LambdaWorkflowState extends WorkflowState {
  layers: string[];
  code: string;
  language: SupportedLanguage;
  libraries: string[];
  memory: number;
  max_execution_time: number;
  saved_input_data?: string;
  saved_backpack_data?: string;
  environment_variables: BlockEnvironmentVariableList;
  reserved_concurrency_count: number | false;
}

export interface BlockEnvironmentVariableList {
  [key: string]: BlockEnvironmentVariable;
}

export interface BlockEnvironmentVariable {
  name: string;
  required: boolean;
  description: string;
  original_id?: string;
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

export interface GlobalHandlers {
  exception_handler?: GlobalExceptionHandler;
}

export interface GlobalExceptionHandler {
  id: string;
}

export interface ProjectConfig {
  environment_variables: ProjectEnvironmentVariableList;
  api_gateway: { gateway_id: string | false };
  version: string;
  logging: { level: ProjectLogLevel };
  default_language: SupportedLanguage;
  project_repo?: string;
  warmup_concurrency_level: number;
}

export interface ProjectEnvironmentVariableList {
  [key: string]: ProjectConfigEnvironmentVariable;
}

export interface ProjectConfigEnvironmentVariable {
  value: string;
  timestamp: number;
}
