export enum ExecutionStatusType {
  EXCEPTION = 'EXCEPTION',
  CAUGHT_EXCEPTION = 'CAUGHT_EXCEPTION',
  SUCCESS = 'SUCCESS'
}

export type ExecutionStatusByType = { [key in ExecutionStatusType]: number };

export interface GetProjectExecutionResult {
  timestamp: number;
  execution_pipeline_totals: ExecutionStatusByType;
  block_executions: BlockExecutionResult[];
  execution_pipeline_id: string;
}

export interface BlockExecutionResult extends ExecutionStatusByType {
  arn: string;
}

export interface GetProjectExecutionLogsPageResult {
  results: ExecutionLogMetadata[];
}

export interface GetProjectExecutionLogObjectsResult {
  results: {
    log_data: RawExecutionLogContents;
    log_id: string;
  }[];
}

export interface ExecutionLogMetadata {
  function_name: string;
  log_id: string;
  s3_key: string;
  timestamp: number;
  type: ExecutionStatusType;
}

export interface ExecutionS3FilenameMetadata {
  executionId: string;
  executionStatus: ExecutionStatusType;
  blockName: string;
  logId: string;
  rawLog: string;
  timestamp: number;
}

export interface RawExecutionLogContents {
  arn: string;
  aws_region: string;
  aws_request_id: string;
  backpack: {};
  execution_pipeline_id: string;
  function_name: string;
  function_version: string;
  group_name: string;
  initialization_time: number;
  input_data: string;
  invoked_function_arn: string;
  memory_limit_in_mb: number;
  name: string;
  program_output: string;
  project_id: string;
  return_data: string;
  stream_name: string;
  timestamp: number;
  type: ExecutionStatusType;
}

export interface ExecutionLogContents {
  arn: string;
  backpack: {};
  input_data: string;
  log_id: string;
  name: string;
  program_output: string;
  project_id: string;
  return_data: string;
  timestamp: number;
  type: ExecutionStatusType;
}
