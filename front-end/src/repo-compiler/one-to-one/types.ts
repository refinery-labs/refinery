import { LambdaWorkflowState, WorkflowFile, WorkflowFileLink } from '@/types/graph';

export type WorkflowFileLookup = Record<string, WorkflowFile>;

export interface LoadedLambdaConfigs {
  sharedFileLinks: WorkflowFileLink[];
  lambdaBlockConfigs: LambdaWorkflowState[];
}
