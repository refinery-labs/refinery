import { ProductionLambdaWorkflowState } from '@/types/production-workflow-types';
import {
  BlockExecutionResult,
  ExecutionLogContents,
  ExecutionLogMetadata,
  ExecutionStatusType
} from '@/types/execution-logs-types';

export interface ProductionExecutionResponse {
  executions: ProjectExecutionsByExecutionId;
  oldestTimestamp: number;
}

export interface ProjectExecution {
  errorCount: number;
  caughtErrorCount: number;
  successCount: number;
  oldestTimestamp: number;
  executionId: string;
  numberOfLogs: number;
  blockExecutionGroupByBlockId: BlockExecutionGroupByBlockId;
}

export interface BlockExecutionGroupByBlockId {
  [key: string]: BlockExecutionGroup;
}

export interface BlockExecutionGroup {
  executionStatus: ExecutionStatusType;
  executionResult: BlockExecutionMetadata;
  timestamp: number;
  totalExecutionCount: number;
  executionId: string;
  blockId: string;
  blockName: string;
  blockArn: string;
}

export interface BlockExecutionMetadata extends BlockExecutionResult {}

export interface ProjectExecutionsByExecutionId {
  [key: string]: ProjectExecution;
}

export interface BlockExecutionPagesByBlockId {
  [key: string]: string[];
}

export interface BlockExecutionTotalsByBlockId {
  [key: string]: number;
}

export interface BlockExecutionLog {
  blockId: string;
  logs: BlockExecutionLogMetadataByLogId;
  pages: string[];
  totalExecutions: number;
}

export interface BlockExecutionLogMetadataByLogId {
  [key: string]: ExecutionLogMetadata;
}

export interface BlockExecutionLogContentsByLogId {
  [key: string]: ExecutionLogContents;
}

export interface BlockExecutionLogsForBlockId {
  [key: string]: ExecutionLogMetadata[];
}

export interface AdditionalBlockExecutionPage {
  blockId: string;
  page: string;
  logs: BlockExecutionLogMetadataByLogId;
}

//////////////////////////////////
// Intermediate data structures //
//////////////////////////////////

export interface BlockExecutionTuple {
  block: ProductionLambdaWorkflowState;
  execution: BlockExecutionResult;
}
