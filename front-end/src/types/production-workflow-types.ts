import {
  SupportedLanguage,
  WorkflowRelationship,
  WorkflowRelationshipType,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { HTTP_METHOD } from '@/constants/api-constants';

// This is missing `id` so it can't extend BaseRefineryResource :(
export interface ProductionDeploymentRefineryProject {
  version: number;
  name: string;
  workflow_states: ProductionWorkflowState[];
  workflow_relationships: ProductionWorkflowRelationship[];
}

export interface ProductionLambdaEnvironmentVariable {
  [key: string]: string;
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
  environment_variables: ProductionLambdaEnvironmentVariable[];
}

export interface ProductionApiEndpointWorkflowState extends ProductionWorkflowState {
  api_path: string;
  http_method: HTTP_METHOD;
  rest_api_id?: string;
}

export interface ProductionApiGatewayResponseWorkflowState extends ProductionWorkflowState {}

export interface ProductionSnsTopicWorkflowState extends ProductionWorkflowState {}

export interface ProductionSqsQueueWorkflow extends ProductionWorkflowState {
  content_based_deduplication: boolean;
  batch_size: number;
}

export interface ProductionScheduleTriggerWorkflowState extends ProductionWorkflowState {
  schedule_expression: string;
  description: string;
  input_string: string;
}
