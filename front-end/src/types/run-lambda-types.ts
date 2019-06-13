import {LambdaWorkflowState, ProjectConfig} from '@/types/graph';

export interface RunCodeBlockLambdaConfig {
  codeBlock: LambdaWorkflowState,
  projectConfig: ProjectConfig
}
