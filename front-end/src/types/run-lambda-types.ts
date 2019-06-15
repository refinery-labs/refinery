import {LambdaWorkflowState, ProjectConfig} from '@/types/graph';
import {ProductionLambdaWorkflowState} from '@/types/production-workflow-types';

export interface RunCodeBlockLambdaConfig {
  codeBlock: LambdaWorkflowState | ProductionLambdaWorkflowState,
  projectConfig: ProjectConfig
}
