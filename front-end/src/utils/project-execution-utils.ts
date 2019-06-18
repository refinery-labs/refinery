import * as R from 'ramda';
import { ProductionExecution } from '@/types/deployment-executions-types';
import { Execution } from '@/types/api-types';
import { mapObjToKeyValueTuple, sortByTimestamp } from '@/lib/ramda-extensions';

export function sortExecutions(arr: ProductionExecution[]) {
  const sorted = sortByTimestamp((i: ProductionExecution) => i.oldest_observed_timestamp, arr);

  // Need to flip it so that the UI has the right order...
  return sorted.reverse();
}

/**
 * Takes in an execution plus an Id and returns a ProductionExecution
 * @param execution Execution to extend
 * @param executionId String to use as Id
 * @returns A new ProductionExecution instance
 */
export function createProductionExecutionFromExecutionAndId(
  executionId: string,
  execution: Execution
): ProductionExecution {
  return {
    executionId,
    ...execution
  };
}

/**
 * Moves the Key of each execution to be a value on the output object. This is encapsulated via the Production Exection type.
 * @param executions Executions to convert data from
 * @returns Object of ProductionExecution instances
 */
export function convertExecutionResponseToProjectExecutions(executions: { [key: string]: Execution }) {
  // Converts from the API type to ProjectExecution
  const unsorted = mapObjToKeyValueTuple(executions, createProductionExecutionFromExecutionAndId);

  // Puts back the key as the executionId. If we didn't do this, the output would just be an array.
  return R.indexBy(p => p.executionId, unsorted);
}
