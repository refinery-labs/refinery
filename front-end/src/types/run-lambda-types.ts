import { LambdaWorkflowState, ProjectConfig, RefineryProject } from '@/types/graph';
import { ProductionLambdaWorkflowState } from '@/types/production-workflow-types';

export interface RunCodeBlockLambdaConfig {
  codeBlock: ProductionLambdaWorkflowState;
  projectConfig: ProjectConfig;
}

export interface RunTmpCodeBlockLambdaConfig {
  codeBlock: LambdaWorkflowState;
  projectConfig: ProjectConfig;
  project: RefineryProject;
}
