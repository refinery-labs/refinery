import * as R from 'ramda';
import {
  BlockExecutionGroup,
  BlockExecutionMetadata,
  ProductionExecution,
  ProjectExecution,
  ProjectExecutions
} from '@/types/deployment-executions-types';
import { Execution, ExecutionStatusType } from '@/types/api-types';
import { groupToArrayBy, mapObjToKeyValueTuple, sortByTimestamp } from '@/lib/ramda-extensions';
import { parseS3LogFilename } from '@/utils/code-block-utils';
import { RefineryProject } from '@/types/graph';

export function sortExecutions(arr: ProjectExecution[]) {
  const sorted = sortByTimestamp((i: ProjectExecution) => i.oldestTimestamp, arr);

  // Need to flip it so that the UI has the right order...
  return sorted.reverse();
}

/**
 * Returns the highest "level" of exception for a given list of executions.
 * For example, if I have a group with 1 failure and 9 successes, I want to return "failure" to identify the group.
 * @param logs List of logs to check execution status for.
 */
function getExecutionStatusForBlockExecutions(logs: BlockExecutionMetadata[]) {
  if (logs.some(ele => ele.executionStatus === ExecutionStatusType.EXCEPTION)) {
    return ExecutionStatusType.EXCEPTION;
  }

  if (logs.some(ele => ele.executionStatus === ExecutionStatusType.CAUGHT_EXCEPTION)) {
    return ExecutionStatusType.CAUGHT_EXCEPTION;
  }

  return ExecutionStatusType.RETURN;
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
 * Takes in a given log filename and associates it with metadata from the given project.
 * Output is a BlockExecutionMetadata instance which ties together an execution with additional metadata from a project.
 * @param project Refinery Project instance that is associated with the given log
 * @param log String of a filename from S3 in the log bucket. Has a mandatory, specific format.
 */
function convertLogFilenameToBlockExecutionMetadata(project: RefineryProject, log: string): BlockExecutionMetadata {
  const logMetadata = parseS3LogFilename(log);

  const block = project.workflow_states.find(ws => ws.name === logMetadata.blockName);

  if (!block) {
    // TODO: Should be throwing..?
    throw new Error('Execution not found for project, unable to locate Block associated with log');
  }

  return {
    ...logMetadata,
    blockId: block.id
  };
}

/**
 * Given a list of BlockExecutions that are associated, creates a BlockExecutionGroup instance.
 * NOTE: The array of metadata must all have the same blockId
 * @param metadata Array of BlockExecutionMetadata objects
 */
function createBlockExecutionGroupWithBlockIdAndMetadata(metadata: BlockExecutionMetadata[]): BlockExecutionGroup {
  if (metadata.length === 0) {
    throw new Error('Cannot create block execution group with missing metadata array');
  }

  const firstBlock = metadata[0];

  if (metadata.some(t => t.blockId !== firstBlock.blockId)) {
    throw new Error('Must not pass block executions for multiple blocks to this function');
  }

  const executionStatus = getExecutionStatusForBlockExecutions(metadata);

  return {
    groupExecutionStatus: executionStatus,
    blockId: firstBlock.blockId,
    blockName: firstBlock.blockName,
    executionId: firstBlock.executionId,
    logs: metadata
  };
}

/**
 * Generates a metadata object that holds information about a given execution in a project.
 * We do this because otherwise the data structure the server hands us to "too close to the metal" and makes our
 * business logic very convoluted with extra code/utils needed everywhere.
 * @param project Project used to get data for the association
 * @param execution A specific execution of a project returned from the API server
 */
function convertExecutionToProjectExecution(
  project: RefineryProject,
  execution: ProductionExecution
): ProjectExecution {
  // Get metadata from S3 filename and convert to metadata data structure
  const metadata: BlockExecutionMetadata[] = execution.logs.map(log =>
    convertLogFilenameToBlockExecutionMetadata(project, log)
  );

  // Takes in the raw array and groups them by blockId. Key is blockId, value is array of executions for that blockId
  const groupedExecutionsByBlockId = groupToArrayBy(t => t.blockId, metadata);

  // Creates a BlockExecutionGroup array to hold metadata about a all executions of a specific block
  const blockExecutionGroups = Object.values(groupedExecutionsByBlockId).map(
    createBlockExecutionGroupWithBlockIdAndMetadata
  );

  // Puts the key as the blockId. If we didn't do this, the output would just be an array.
  const blockExecutionGroupIndexByBlockId = R.indexBy(p => p.blockId, blockExecutionGroups);

  return {
    error: execution.error,
    oldestTimestamp: execution.oldest_observed_timestamp,
    executionId: execution.executionId,
    numberOfLogs: execution.logs.length,
    logsGroupedByBlockId: blockExecutionGroupIndexByBlockId
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
  executions: ProjectExecutions
) {
  // Converts from the API type to ProjectExecution
  const productionExecutions = mapObjToKeyValueTuple(createProductionExecutionFromExecutionAndId, executions);

  // List of project execution instances with metadata fully associated from the specified project
  const unfilteredProjectExecutions = productionExecutions.map(execution => {
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
