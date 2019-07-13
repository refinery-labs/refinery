import * as R from 'ramda';
import {
  BlockExecutionGroup,
  BlockExecutionTuple,
  ProjectExecution
} from '@/types/deployment-executions-types';
import {BlockExecutionResult, ExecutionStatusType, GetProjectExecutionResult} from '@/types/api-types';
import {sortByTimestamp} from '@/lib/ramda-extensions';
import {RefineryProject, WorkflowStateType} from '@/types/graph';
import {ProductionLambdaWorkflowState} from '@/types/production-workflow-types';

export function sortExecutions(arr: ProjectExecution[]) {
  const sorted = sortByTimestamp((i: ProjectExecution) => i.oldestTimestamp, arr);

  // Need to flip it so that the UI has the right order...
  return sorted.reverse();
}

export function getProductionLambdaBlocksFromProject(project: RefineryProject) {
  // Make an array of Production Lambda blocks
  return project.workflow_states.filter(
    block => block.type === WorkflowStateType.LAMBDA && (block as ProductionLambdaWorkflowState).arn
  ) as ProductionLambdaWorkflowState[];
}

export function pairExecutionWithBlock(
  project: RefineryProject,
  executionResult: GetProjectExecutionResult
) {
  const lambdaBlocks = getProductionLambdaBlocksFromProject(project);

  // Get a ghetto "tuple" of type [block, execution] by pairing an execution to a block by ARN
  return executionResult.block_executions.map(execution => {
    const matchingBlock = lambdaBlocks.find(block => block.arn === execution.arn);

    if (!matchingBlock) {
      throw new Error('Could not find matching block for block execution');
    }

    return {block: matchingBlock, execution};
  });
}

function getExecutionStatusForBlockExecution(execution: BlockExecutionResult) {
  if (execution.EXCEPTION > 0) {
    return ExecutionStatusType.EXCEPTION;
  }

  if (execution.CAUGHT_EXCEPTION > 0) {
    return ExecutionStatusType.CAUGHT_EXCEPTION;
  }

  return ExecutionStatusType.SUCCESS;
}

/**
 * Given a RefineryProject and GetProjectExecutionResult, return a mapping of blockId -> BlockExecutionGroup
 * @param project Project to pull data from
 * @param executionResult List of results to use for the association
 */
function createLogsGroupedByBlockId(
  project: RefineryProject,
  executionResult: GetProjectExecutionResult
) {

  const pairedExecutionWithBlock = pairExecutionWithBlock(project, executionResult);

  // Put the ID of the element as the key and the execution result as the value.
  const executionTuplesByBlockId = pairedExecutionWithBlock.reduce((acc, elem) => {
    acc[elem.block.id] = elem;
    return acc;
  }, {} as {[key: string]: BlockExecutionTuple});

  // Iterate through the Object's values and create a BlockExecutionGroup from the values.
  return R.mapObjIndexed(({block, execution}: BlockExecutionTuple) => {
    const totalExecutionCount = execution.EXCEPTION + execution.CAUGHT_EXCEPTION + execution.SUCCESS;

    const out: BlockExecutionGroup = {
      executionStatus: getExecutionStatusForBlockExecution(execution),
      executionResult: execution,
      totalExecutionCount,
      executionId: executionResult.execution_pipeline_id,
      blockId: block.id,
      blockName: block.name,
      blockArn: execution.arn
    };
    return out;
  }, executionTuplesByBlockId);
}

/**
 * Generates a metadata object that holds information about a given execution in a project.
 * We do this because otherwise the data structure the server hands us to "too close to the metal" and makes our
 * business logic very convoluted with extra code/utils needed everywhere.
 * @param project Project used to get data for the association
 * @param executionResult A specific execution of a project returned from the API server
 */
function convertExecutionToProjectExecution(
  project: RefineryProject,
  executionResult: GetProjectExecutionResult
): ProjectExecution {


  const totals = executionResult.execution_pipeline_totals;

  const numberOfLogs = totals.EXCEPTION + totals.CAUGHT_EXCEPTION + totals.SUCCESS;

  return {
    error: totals.EXCEPTION > 0,
    oldestTimestamp: executionResult.timestamp,
    executionId: executionResult.execution_pipeline_id,
    blockExecutionGroupByBlockId: createLogsGroupedByBlockId(project, executionResult),
    numberOfLogs
  };
}

/**
 * Moves the Key of each execution to be a value on the output object. This is encapsulated via the Production Execution type.
 * @param project Project to lookup block information for the logs from.
 * @param executions Executions to convert data from
 * @returns Object of ProductionExecution instances
 * @throws Will throw whenever an invalid state is detected
 */
export function convertExecutionResponseToProjectExecutionGroup(
  project: RefineryProject,
  executions: GetProjectExecutionResult[]
) {

  // List of project execution instances with metadata fully associated from the specified project
  const unfilteredProjectExecutions = executions.map(execution => {
    try {
      return convertExecutionToProjectExecution(project, execution);
    } catch (e) {
      console.log('Failed to convert project execution, likely invalid logs for the current project', e);
      return null;
    }
  });

  // If there were any exceptions converting an execution, filter it out
  const projectExecutions = unfilteredProjectExecutions.filter(t => t !== null) as ProjectExecution[];

  // Puts the key as the executionId. If we didn't do this, the output would just be an array.
  return R.indexBy(p => p.executionId, projectExecutions);
}
