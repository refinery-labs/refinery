import {
  LambdaWorkflowState,
  ProjectConfig,
  ProjectEnvironmentVariableList,
  SupportedLanguage,
  WorkflowFile,
  WorkflowRelationship,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import {
  ProductionGlobalHandlers,
  ProductionWorkflowFile,
  ProductionWorkflowFileLink,
  ProductionWorkflowRelationship,
  ProductionWorkflowState
} from '@/types/production-workflow-types';
import {
  ExecutionLogMetadata,
  ExecutionStatusType,
  GetProjectExecutionLogObjectsResult,
  GetProjectExecutionLogsPageResult,
  GetProjectExecutionResult
} from '@/types/execution-logs-types';
import ImportableRefineryProject from '@/types/export-project';
import * as moment from 'moment';
import Base = moment.unitOfTime.Base;
import SharedFiles from '@/components/ProjectEditor/SharedFiles';
import { DemoTooltip } from '@/types/demo-walkthrough-types';

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
  versions: SearchSavedProjectVersionMetadata[];
  deployment: string | null;
  id: string;
  name: string;
}

export interface SearchSavedProjectVersionMetadata {
  timestamp: number;
  version: number;
}

// CreateSQSQueueTrigger
export interface CreateSQSQueueTriggerRequest extends BaseApiRequest {
  batch_size: number;
  lambda_arn: string;
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
  force_redeploy: boolean;
}

export enum DeployDiagramResponseCode {
  AccessDenied = 'ACCESS_DENIED',
  DeploymentLockFailure = 'DEPLOYMENT_LOCK_FAILURE'
}

export interface DeployDiagramResponse extends BaseApiResponse {
  code?: DeployDiagramResponseCode;
  result: DeployDiagramResponseResult;
}

export interface DeployDiagramResponseResult {
  project_id: string;
  deployment_id: string;
  deployment_success: boolean;
  diagram_data: DiagramData;
  exceptions?: DeploymentException[];
}

export interface DiagramData {
  workflow_relationships: WorkflowRelationship[];
  version: number;
  name: string;
  workflow_states: WorkflowState[];
}

export interface DeploymentException {
  id: string;
  name: string;
  type: string;
  exception: string;
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
  result: GetLatestProjectDeploymentResult | null;
}

export interface GetLatestProjectDeploymentResult {
  deployment_json: ProductionDeploymentRefineryProjectJson;
  project_id: string;
  id: string;
  timestamp: number;
}

export interface ProductionDeploymentRefineryProjectJson {
  version: number;
  name: string;
  readme: string;
  workflow_states: ProductionWorkflowState[];
  workflow_relationships: ProductionWorkflowRelationship[];
  workflow_files: ProductionWorkflowFile[];
  workflow_file_links: ProductionWorkflowFileLink[];
  global_handlers: ProductionGlobalHandlers;
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
  execution_pipeline_id: string;
  arn: string;
  project_id: string;
  oldest_timestamp: number;
}

export interface GetProjectExecutionLogsResponse extends BaseApiResponse {
  result: GetProjectExecutionLogsResult;
}

export interface GetProjectExecutionLogsResult {
  results: ExecutionLogMetadata[];
  pages: string[];
}

/**
 * Get past execution ID(s) for a given deployed project and their respective metadata.
 */
export interface GetProjectExecutionsRequest extends BaseApiRequest {
  oldest_timestamp: number;
  project_id: string;
}

export interface GetProjectExecutionsResponse extends BaseApiResponse {
  result: GetProjectExecutionResult[];
}

// GetProjectExecutionLogsPage
export interface GetProjectExecutionLogsPageRequest extends BaseApiRequest {
  id: string;
}

export interface GetProjectExecutionLogsPageResponse extends BaseApiResponse {
  result: GetProjectExecutionLogsPageResult;
}

// GetProjectExecutionLogObjects
export interface GetProjectExecutionLogObjectsRequest extends BaseApiRequest {
  // min length: 1, max length 50
  logs_to_fetch: {
    s3_key: string;
    log_id: string;
  }[];
}

export interface GetProjectExecutionLogObjectsResponse extends BaseApiResponse {
  result: GetProjectExecutionLogObjectsResult;
}

// GetSavedProject
export interface GetSavedProjectRequest extends BaseApiRequest {
  project_id: string;
  version?: number;
  demo_project?: boolean;
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
  result: Array<InfraTearDownResult>;
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
  backpack: string;
  execution_id?: string;
  debug_id?: string;
}

export interface RunLambdaResponse extends BaseApiResponse {
  failure_msg?: string;
  failure_reason?: RunLambdaFailure;
  result: RunLambdaResult;
}

export enum RunLambdaFailure {
  InvalidInputJson = 'InvalidInputJson',
  InvalidBackpackJson = 'InvalidBackpackJson',
  UnknownError = 'UnknownError'
}

export interface RunLambdaResult {
  is_error: boolean;
  version: string;
  logs: string;
  truncated: boolean;
  status_code: number;
  arn: string;
  /**
   * This is the JSON formatted data returned from the code execution result.
   */
  returned_data: string;
}

/**
 * Build, deploy, and run an AWS lambda function.
 * Always upon completion the Lambda should be deleted!
 */
export interface RunTmpLambdaRequest extends BaseApiRequest {
  code: string;
  environment_variables: RunTmpLambdaEnvironmentVariable[];
  input_data: string;
  backpack: string;
  language: SupportedLanguage;
  layers: any[];
  libraries: any[];
  max_execution_time: number;
  memory: number;
  block_id: string;
  debug_id: string;
  shared_files: WorkflowFile[];
}

export interface RunTmpLambdaEnvironmentVariable {
  key: string;
  value: string;
}

// This is the same thing as RunLambdaResponse but gonna leave the types split out and solve with inheritance
export interface RunTmpLambdaResponse extends RunLambdaResponse {
  msg?: string;
  log_output?: string;
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
  code?: string;
  msg?: string;
}

// RenameProject
export interface RenameProjectRequest extends BaseApiRequest {
  project_id: string;
  name: string;
}

export interface RenameProjectResponse extends BaseApiResponse {
  code: RenameProjectResponseCode;
  msg: string;
}

export enum RenameProjectResponseCode {
  ProjectNameExists = 'PROJECT_NAME_EXISTS',
  MissingProject = 'MISSING_PROJECT',
  AccessDenied = 'ACCESS_DENIED',
  RenameSuccessful = 'RENAME_SUCCESSFUL'
}

// SaveProjectConfig
export interface SaveProjectConfigRequest extends BaseApiRequest {
  project_id: string | boolean;
  config: string;
}

export interface SaveProjectConfigResponse extends BaseApiResponse {
  project_id: string;
}

/**
 * Create a Lambda to save for later use.
 */
export interface SavedLambdaCreateRequest {
  code: string;
  description: string;
  language: SupportedLanguage;
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
  environment_variables: ProjectEnvironmentVariableList;
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
  intercom_user_hmac: string;
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

// AuthenticateWithGithub
export interface AuthenticateWithGithubRequest extends BaseApiRequest {
  // Empty
}

export interface AuthenticateWithGithubResponse extends BaseApiResponse {
  // Empty
}

// Billing Get Credits
export interface GetPaymentMethodsRequest extends BaseApiRequest {
  // Empty
}

export interface GetPaymentMethodsResponse extends BaseApiResponse {
  cards: PaymentCardResult[];
}

export interface PaymentCardResult {
  id: string;
  brand: string;
  country: string;
  exp_month: number;
  exp_year: number;
  last4: string;
  is_primary: boolean;
}

// Billing delete card
export interface DeletePaymentMethodRequest extends BaseApiRequest {
  id: string;
}

export interface DeletePaymentMethodResponse extends BaseApiResponse {
  msg: string;
}

// Billing make primary card
export interface MakePrimaryMethodRequest extends BaseApiRequest {
  id: string;
}

export interface MakePrimaryMethodResponse extends BaseApiResponse {
  msg: string;
}

// Billing add card
export interface AddPaymentMethodRequest extends BaseApiRequest {
  // Nothing
}

export interface AddPaymentMethodResponse extends BaseApiResponse {
  msg: string;
}

// Get latest monthly bill
export interface GetLatestMonthlyBillRequest extends BaseApiRequest {
  billing_month: string;
}

export interface BillTotal {
  bill_total: string;
  unit: string;
}

export interface BillChargeItem {
  service_name: string;
  total: string;
  unit: string;
}

export interface BillingData {
  bill_total: BillTotal;
  service_breakdown: BillChargeItem[];
}

export interface GetLatestMonthlyBillResponse extends BaseApiResponse {
  billing_data: BillingData;
}

export interface GetBuildStatusRequest extends BaseApiRequest {
  libraries: string[];
  language: SupportedLanguage;
}

export interface GetBuildStatusResponse extends BaseApiResponse {
  is_already_cached: boolean;
}

export interface StartLibraryBuildRequest extends BaseApiRequest {
  libraries: string[];
  language: SupportedLanguage;
}

export interface StartLibraryBuildResponse extends BaseApiResponse {}

// GetConsoleCredentialsRequest
export interface GetConsoleCredentialsRequest extends BaseApiRequest {}

export interface ConsoleCredentials {
  username: string;
  password: string;
  signin_url: string;
}

export interface GetConsoleCredentialsResponse extends BaseApiResponse {
  console_credentials: ConsoleCredentials;
}

// StashStateLog
export interface StashStateLogRequest extends BaseApiRequest {
  session_id: string;
  state: object;
}

export interface StashStateLogResponse extends BaseApiResponse {}

// CreateSavedBlock for creating new saved block versions
export interface CreateSavedBlockRequest extends BaseApiRequest {
  id?: string;
  description?: string;
  block_object: WorkflowState;
  version?: number;
  share_status?: SharedBlockPublishStatus;
  shared_files: WorkflowFile[];
  save_type: SavedBlockSaveType;
}

export interface CreateSavedBlockResponse extends BaseApiResponse {
  block: SavedBlockSearchResult;
}

export enum SharedBlockPublishStatus {
  PUBLISHED = 'PUBLISHED',
  PRIVATE = 'PRIVATE'
}

export enum SavedBlockSaveType {
  CREATE = 'CREATE',
  UPDATE = 'UPDATE',
  FORK = 'FORK'
}

// SearchSavedBlocks
export interface SearchSavedBlocksRequest extends BaseApiRequest {
  search_string: string;
  share_status: SharedBlockPublishStatus;
  language: string;
}

export interface SearchSavedBlocksResponse extends BaseApiResponse {
  results: SavedBlockSearchResult[];
}

export interface SavedBlockSearchResult {
  id: string;
  description: string;
  name: string;
  share_status: SharedBlockPublishStatus;
  type: WorkflowStateType;
  block_object: WorkflowState;
  shared_files: WorkflowFile[];
  version: number;
  timestamp: number;
}

// DeleteSavedBlock
export interface DeleteSavedBlockRequest extends BaseApiRequest {
  id: string;
}

export interface DeleteSavedBlockResponse extends BaseApiResponse {}

// SavedBlockStatusCheck
export interface SavedBlockStatusCheckRequest extends BaseApiRequest {
  block_ids: string[];
}

export interface SavedBlockStatusCheckResponse extends BaseApiResponse {
  results: SavedBlockStatusCheckResult[];
}

export interface SavedBlockStatusCheckResult {
  id: string;
  is_block_owner: boolean;
  description: string;
  name: string;
  share_status: SharedBlockPublishStatus;
  block_object: WorkflowState;
  version: number;
  timestamp: number;
}

// CreateProjectShortlink
export interface CreateProjectShortlinkRequest extends BaseApiRequest {
  diagram_data: ImportableRefineryProject;
}

export interface CreateProjectShortlinkResponse extends BaseApiResponse {
  result: {
    msg: string;
    project_short_link_id: string;
  };
}

// GetProjectShortlink
export interface GetProjectShortlinkRequest extends BaseApiRequest {
  project_short_link_id: string;
}

export interface GetProjectShortlinkResponse extends BaseApiResponse {
  result: {
    project_short_link_id: string;
    diagram_data: ImportableRefineryProject;
  };
}

// Lambda live log streaming Websocket message
export enum LambdaDebuggingWebsocketSources {
  Lambda = 'LAMBDA',
  Server = 'SERVER'
}

export enum LambdaDebuggingWebsocketActions {
  Output = 'OUTPUT',
  Heartbeat = 'HEARTBEAT'
}

export interface LambdaDebuggingWebsocketMessage {
  body: string;
  timestamp: number;
  source: LambdaDebuggingWebsocketSources;
  version: string;
  action: LambdaDebuggingWebsocketActions;
  debug_id: string | null;
}
