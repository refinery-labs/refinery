import {
  LambdaWorkflowState,
  ProjectConfig,
  ProjectEnvironmentVariableConfig,
  WorkflowRelationship,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import {
  ProductionDeploymentRefineryProject,
  ProductionWorkflowState
} from '@/types/production-workflow-types';

export interface BaseApiResponse {
  success: boolean;
}

export interface BaseApiRequest {}

// SearchSavedProjects
export interface SearchSavedProjectsRequest extends BaseApiRequest {
  query: string | null;
}

export interface SearchSavedProjectsResponse extends BaseApiResponse {
  results: SearchSavedProjectsResult[];
}

export interface SearchSavedProjectsResult {
  timestamp: number;
  versions: number[];
  id: string;
  name: string;
}

// CreateSQSQueueTrigger
export interface CreateSQSQueueTriggerRequest extends BaseApiRequest {
  batch_size: number;
  content_based_deduplication: boolean;
  lambda_arn: string;
  queue_name: string;
}

export interface CreateSQSQueueTriggerResponse extends BaseApiResponse {
  queue_url: string;
}

/**
 * Creates a scheduled trigger for a given SFN or Lambda.
 */
export interface CreateScheduleTriggerRequest {
  description: string;
  name: string;
  schedule_expression: string;
  target_arn: string;
  target_id: string;
  target_type: string;
  input_string: string;
}

export interface CreateScheduleTriggerResponse extends BaseApiResponse {
  result: CreateScheduleTriggerResult;
}

export interface CreateScheduleTriggerResult {
  rule_arn: string;
  url: string;
}

// DeleteDeploymentsInProject
export interface DeleteDeploymentsInProjectRequest extends BaseApiRequest {
  project_id: string;
}

export interface DeleteDeploymentsInProjectResponse extends BaseApiResponse {
  // Only hold success
}

// DeleteSavedProject
export interface DeleteSavedProjectRequest extends BaseApiRequest {
  id: string;
}

export interface DeleteSavedProjectResponse extends BaseApiResponse {}

// DeployDiagram
export interface DeployDiagramRequest extends BaseApiRequest {
  project_name: string;
  project_id: string;
  project_config: ProjectConfig;
  diagram_data: string;
}

export interface DeployDiagramResponse extends BaseApiResponse {
  result: DeployDiagramResponseResult;
}

export interface DeployDiagramResponseResult {
  project_id: string;
  deployment_id: string;
  deployment_success: boolean;
  diagram_data: DiagramData;
}

export interface DiagramData {
  workflow_relationships: WorkflowRelationship[];
  version: number;
  name: string;
  workflow_states: WorkflowState[];
}

// GetCloudWatchLogsForLambda
export interface GetCloudWatchLogsForLambdaRequest extends BaseApiRequest {
  arn: string;
}

export interface GetCloudWatchLogsForLambdaResponse extends BaseApiResponse {
  result: GetCloudWatchLogsForLambdaResult;
}

export interface GetCloudWatchLogsForLambdaResult {
  truncated: boolean;
  log_output: string;
}

// GetLatestProjectDeployment
export interface GetLatestProjectDeploymentRequest extends BaseApiRequest {
  project_id: string;
}

export interface GetLatestProjectDeploymentResponse extends BaseApiResponse {
  deployment_json: ProductionDeploymentRefineryProject;
  project_id: string;
  id: string;
  timestamp: number;
}

// GetProjectConfig
export interface GetProjectConfigRequest extends BaseApiRequest {
  project_id: string;
}

export interface GetProjectConfigResponse extends BaseApiResponse {
  result: ProjectConfig;
}

// GetProjectExecutionLogs
export interface GetProjectExecutionLogsRequest extends BaseApiRequest {
  logs: string[];
}

export interface GetProjectExecutionLogsResponse extends BaseApiResponse {
  result: { [key: string]: GetProjectExecutionLogsResult };
}

export interface GetProjectExecutionLogsResult {
  stream_name: string;
  memory_limit_in_mb: number;
  initialization_time: number;
  aws_request_id: string;
  name: string;
  timestamp: number;
  aws_region: string;
  group_name: string;
  project_id: string;
  type: string;
  id: string;
  invoked_function_arn: string;
  data: ExecutionLogData;
  function_version: string;
  arn: string;
  function_name: string;
}

export interface ExecutionLogData {
  input_data: string;
  return_data: boolean;
  output: string;
}

/**
 * Get past execution ID(s) for a given deployed project and their respective metadata.
 */
export interface GetProjectExecutionsRequest extends BaseApiRequest {
  continuation_token?: string;
  project_id: string;
}

export interface GetProjectExecutionsResponse extends BaseApiResponse {
  result: GetProjectExecutionsResponseResult;
}

export interface GetProjectExecutionsResponseResult {
  continuation_token: boolean;
  executions: { [key: string]: Execution };
}

export interface Execution {
  oldest_observed_timestamp: number;
  logs: string[];
  error: boolean;
}

// GetSavedProject
export interface GetSavedProjectRequest extends BaseApiRequest {
  project_id: string;
  version?: number;
}

export interface GetSavedProjectResponse extends BaseApiResponse {
  project_json: string;
  version: number;
  project_id: string;
  success: boolean;
}

// InfraCollisionCheck
export interface InfraCollisionCheckRequest extends BaseApiRequest {
  diagram_data: DiagramData;
}

export interface InfraCollisionCheckResponse extends BaseApiResponse {
  result: InfraCollisionResult[];
}

export interface InfraCollisionResult {
  id: string;
  arn: string;
  name: string;
  type: WorkflowStateType;
}

// InfraTearDown
export interface InfraTearDownRequest extends BaseApiRequest {
  teardown_nodes: ProductionWorkflowState[];
  project_id: string;
}

export interface InfraTearDownResponse extends BaseApiResponse {
  result: Array<InfraTearDownResult | string>;
}

export interface InfraTearDownResult {
  deleted: boolean;
  type: string;
  id: string;
  arn: string;
  name: string;
}

/**
 * Run a Lambda which has been deployed in production.
 */
export interface RunLambdaRequest extends BaseApiRequest {
  arn: string;
  input_data: string;
}

export interface RunLambdaResponse extends BaseApiResponse {
  result: RunLambdaResult;
}

export interface RunLambdaResult {
  error: RunLambdaError;
  retries: number;
  is_error: boolean;
  version: string;
  logs: string;
  truncated: boolean;
  status_code: number;
  request_id: string;
  response: boolean;
  arn: string;
}

export interface RunLambdaError {
  message: string;
  type: string;
  trace: string;
}

/**
 * Build, deploy, and run an AWS lambda function.
 * Always upon completion the Lambda should be deleted!
 */
export interface RunTmpLambdaRequest extends BaseApiRequest {
  code: string;
  environment_variables: any[];
  input_data: any;
  language: string;
  layers: any[];
  libraries: any[];
  max_execution_time: number;
  memory: number;
}

export interface RunTmpLambdaResponse extends BaseApiResponse {
  result: RunTmpLambdaResponseResult;
}

export interface RunTmpLambdaResponseResult {
  error: Error;
  retries: number;
  is_error: boolean;
  version: string;
  logs: string;
  truncated: boolean;
  status_code: number;
  request_id: string;
  response: boolean;
  arn: string;
}

export interface Error {
  message?: string;
  type?: string;
  trace?: Array<Array<number | string>>;
}

// SaveProject
export interface SaveProjectRequest extends BaseApiRequest {
  /**
   * If specified, saves the project with a given id.
   * TODO: Is this a mis-feature?
   * TODO: Make this nullable instead of using false
   */
  project_id: string | boolean;
  /**
   * JSON serialized DiagramData
   * TODO: Make this part of the JSON object instead of a string
   */
  diagram_data: string;
  /**
   * Version to save the project with
   * TODO: Make this nullable instead of using false
   */
  version: string | boolean;
  /**
   * JSON serialized config data (env variables and sheit)
   * TODO: Make this part of the JSON object instead of a string
   */
  config: string;
}

export interface SaveProjectResponse extends BaseApiResponse {
  project_version: number;
  project_id: string;
}

/**
 * Create a Lambda to save for later use.
 */
export interface SavedLambdaCreateRequest {
  code: string;
  description: string;
  language: string;
  libraries: string[];
  max_execution_time: number;
  memory: number;
  name: string;
}

export interface SavedLambdaCreateResponse extends BaseApiResponse {
  id: string;
}

/**
 * Delete a saved Lambda
 */
export interface SavedLambdaDeleteRequest extends BaseApiRequest {
  id: string;
}

export interface SavedLambdaDeleteResponse extends BaseApiResponse {
  // Only has success
}

/**
 * Free text search of saved Lambda, returns matching results.
 */
export interface SavedLambdaSearchRequest extends BaseApiRequest {
  query: string;
}

export interface SavedLambdaSearchResponse extends BaseApiResponse {
  results: SavedLambdaSearchResponseResult[];
}

export interface SavedLambdaSearchResponseResult extends LambdaWorkflowState {
  description: string;
  timestamp: number;
}

// UpdateEnvironmentVariables
export interface UpdateEnvironmentVariablesRequest extends BaseApiRequest {
  project_id: string;
  arn: string;
  environment_variables: ProjectEnvironmentVariableConfig;
}

export interface UpdateEnvironmentVariablesResponse extends BaseApiResponse {
  result: UpdateEnvironmentVariablesResult;
}

export interface UpdateEnvironmentVariablesResult {
  // This is potentially not a string, it will be type DiagramData if it is not.
  deployment_diagram: string;
}

// Health
export interface HealthCheckRequest extends BaseApiRequest {
  // Empty
}

export interface HealthCheckResponse extends BaseApiResponse {
  status: string;
}

// GetAuthenticationStatus
export interface GetAuthenticationStatusRequest extends BaseApiRequest {
  // Empty
}

export interface GetAuthenticationStatusResponse extends BaseApiResponse {
  authenticated: boolean;
  name?: string;
  email?: string;
  permission_level?: string;
  trial_information?: TrialInformation;
}

export interface TrialInformation {
  trial_end_timestamp: number;
  trial_started_timestamp: number;
  trial_over: boolean;
  is_using_trial: boolean;
}

// NewRegistration
export interface NewRegistrationRequest extends BaseApiRequest {
  organization_name: string | undefined;
  name: string;
  email: string;
  phone: string | undefined;
  stripe_token: string;
}

export interface NewRegistrationResponse extends BaseApiResponse {
  result: NewRegistrationResult;
}

export interface NewRegistrationResult {
  msg: string;
  code: NewRegistrationErrorType;
}

export enum NewRegistrationErrorType {
  INVALID_EMAIL = 'INVALID_EMAIL',
  USER_ALREADY_EXISTS = 'USER_ALREADY_EXISTS'
}

// Login
export interface LoginRequest extends BaseApiRequest {
  email: string;
}

export interface LoginResponse extends BaseApiResponse {
  msg: string;
}

// Logout
export interface LogoutRequest extends BaseApiRequest {
  // Empty
}

export interface LogoutResponse extends BaseApiResponse {
  // Empty
}
