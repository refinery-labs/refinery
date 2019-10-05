import { LibraryBuildArguments, startLibraryBuild } from '@/store/fetchers/api-helpers';
import { LambdaWorkflowState, WorkflowState, WorkflowStateType } from '@/types/graph';
import * as R from 'ramda';

/**
 * For a given set of blocks, kicks off a check to setup the libraries for the blocks to run.
 * This helps with deployment times + inline execution speed. Better UX for users.
 * This function de-dedupes the builds needed to be kicked off.
 * @param blocks Array of blocks to run build for. Builds are only run for Code Blocks.
 */
export function kickOffLibraryBuildForBlocks(blocks: WorkflowState[]) {
  // Hmm, the static typing here is quite tricky!
  R.pipe<
    WorkflowState[],
    WorkflowState[],
    LambdaWorkflowState[],
    LambdaWorkflowState[],
    LibraryBuildArguments[],
    LibraryBuildArguments[],
    LibraryBuildArguments[]
  >(
    // Filter down to only code blocks
    R.filter((block: WorkflowState) => block.type === WorkflowStateType.LAMBDA),
    // Cast the blocks to the right type.
    R.map((block: WorkflowState) => block as LambdaWorkflowState),
    // Filter down to only blocks with libraries
    R.filter((codeBlock: LambdaWorkflowState) => codeBlock.libraries.length > 0),
    // Return a build config for each block
    R.map(codeBlock => ({
      language: codeBlock.language,
      libraries: codeBlock.libraries
    })),
    // De-dupe any duplicate libraries by comparing their JSON representation
    R.uniqBy(JSON.stringify),
    // Kick off the library builds for every block in the list
    R.forEach(startLibraryBuild)
  )(blocks);
}
