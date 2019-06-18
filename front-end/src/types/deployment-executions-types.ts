import { Execution } from '@/types/api-types';

export interface ProductionExecution extends Execution {
  executionId: string;
}

export interface ProductionExecutionResponse {
  executions: { [key: string]: ProductionExecution };
  continuationToken: string | null;
}
