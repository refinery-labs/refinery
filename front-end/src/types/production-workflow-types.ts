import {
  RefineryProject,
  SupportedLanguage,
  WorkflowRelationship,
  WorkflowRelationshipType,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { HTTP_METHOD } from '@/constants/api-constants';

export interface ProductionDeploymentRefineryProject extends RefineryProject {
  workflow_states: ProductionWorkflowState[];
  workflow_relationships: ProductionWorkflowRelationship[];
}

export interface ProductionLambdaEnvironmentVariable {
  name: string;
  value: string;
  description: string;
  required: boolean;
}

export interface ProductionWorkflowState extends WorkflowState {
  arn?: string;
  transitions: ProductionTransitionLookup;
}

export interface ProductionWorkflowRelationship extends WorkflowRelationship {}

export interface ProductionTransition {
  type: WorkflowStateType;
  arn: string;
}

export type ProductionTransitionLookup = { [key in WorkflowRelationshipType]: ProductionTransition[] };

export interface ProductionLambdaWorkflowState extends ProductionWorkflowState {
  layers: string[];
  code: string;
  language: SupportedLanguage;
  libraries: string[];
  memory: number;
  max_execution_time: number;
  saved_input_data?: string;
  environment_variables: { [key: string]: ProductionLambdaEnvironmentVariable };
  reserved_concurrency_limit: number | false;
}

export interface ProductionApiEndpointWorkflowState extends ProductionWorkflowState {
  api_path: string;
  http_method: HTTP_METHOD;
  url: string;
  rest_api_id?: string;
}

export interface ProductionApiGatewayResponseWorkflowState extends ProductionWorkflowState {}

export interface ProductionSnsTopicWorkflowState extends ProductionWorkflowState {}

export interface ProductionSqsQueueWorkflow extends ProductionWorkflowState {
  batch_size: number;
}

export interface ProductionScheduleTriggerWorkflowState extends ProductionWorkflowState {
  schedule_expression: string;
  description: string;
  input_string: string;
}
