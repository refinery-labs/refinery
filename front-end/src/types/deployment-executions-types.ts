import { Execution, ExecutionStatusType } from '@/types/api-types';

export interface ProductionExecutionResponse {
  executions: { [key: string]: ProjectExecution };
  continuationToken: string | null;
}

export interface ProjectExecution {
  error: boolean;
  oldestTimestamp: number;
  executionId: string;
  numberOfLogs: number;
  logsGroupedByBlockId: { [key: string]: BlockExecutionGroup };
}

export interface BlockExecutionGroup {
  groupExecutionStatus: ExecutionStatusType;
  executionId: string;
  blockId: string;
  blockName: string;
  logs: BlockExecutionMetadata[];
}

export interface BlockExecutionMetadata {
  executionId: string;
  executionStatus: ExecutionStatusType;
  blockName: string;
  blockId: string;
  logId: string;
  rawLog: string;
  timestamp: number;
}

//////////////////////////////////
// Intermediate data structures //
//////////////////////////////////

export interface ProjectExecutions {
  [key: string]: Execution;
}

export interface ProductionExecution extends Execution {
  executionId: string;
}

export interface ExecutionLogMetadata {
  executionId: string;
  executionStatus: ExecutionStatusType;
  blockName: string;
  logId: string;
  rawLog: string;
  timestamp: number;
}
