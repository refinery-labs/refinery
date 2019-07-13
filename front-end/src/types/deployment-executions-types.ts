import {
  GetProjectExecutionResult,
  ExecutionStatusType,
  BlockExecutionResult,
  ExecutionLogContents
} from '@/types/api-types';
import {ProductionLambdaWorkflowState} from '@/types/production-workflow-types';

export interface ProductionExecutionResponse {
  executions: ProjectExecutionsByExecutionId;
  oldestTimestamp: number;
}

export interface ProjectExecution {
  error: boolean;
  oldestTimestamp: number;
  executionId: string;
  numberOfLogs: number;
  blockExecutionGroupByBlockId: BlockExecutionGroupByBlockId;
}

export interface BlockExecutionGroupByBlockId {
  [key: string]: BlockExecutionGroup
}

export interface BlockExecutionGroup {
  executionStatus: ExecutionStatusType;
  executionResult: BlockExecutionMetadata;
  totalExecutionCount: number;
  executionId: string;
  blockId: string;
  blockName: string;
  blockArn: string;
}

export interface BlockExecutionMetadata extends BlockExecutionResult {
}

export interface ProjectExecutionsByExecutionId {
  [key: string]: ProjectExecution
}

export interface BlockExecutionPagesByBlockId {
  [key: string]: string[]
}

export interface BlockExecutionTotalsByBlockId {
  [key: string]: number
}

export interface BlockExecutionLog {
  blockId: string;
  logs: BlockExecutionLogContentsByLogId;
  pages: string[];
  totalExecutions: number;
}

export interface BlockExecutionLogContentsByLogId {
  [key: string]: ExecutionLogContents
}

export interface BlockExecutionLogsForBlockId {
  [key: string]: string[]
}

export interface AdditionalBlockExecutionPage {
  blockId: string,
  page: string,
  logs: { [key: string]: ExecutionLogContents }
}

//////////////////////////////////
// Intermediate data structures //
//////////////////////////////////

export interface ProjectExecutions {
  [key: string]: GetProjectExecutionResult;
}

export interface BlockExecutionTuple {
  block: ProductionLambdaWorkflowState,
  execution: BlockExecutionResult
}

export interface ExecutionLogMetadata {
  executionId: string;
  executionStatus: ExecutionStatusType;
  blockName: string;
  logId: string;
  rawLog: string;
  timestamp: number;
}
