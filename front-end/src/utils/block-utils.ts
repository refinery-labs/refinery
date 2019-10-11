import uuid from 'uuid/v4';
import {
  BlockEnvironmentVariable,
  BlockEnvironmentVariableList,
  LambdaWorkflowState,
  ProjectConfig,
  ProjectConfigEnvironmentVariable,
  ProjectEnvironmentVariableList,
  WorkflowFile,
  WorkflowRelationship,
  WorkflowRelationshipType,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { CURRENT_BLOCK_SCHEMA, CURRENT_TRANSITION_SCHEMA } from '@/constants/graph-constants';
import { BlockTypeToDefaultState, blockTypeToDefaultStateMapping } from '@/constants/project-editor-constants';
import { deepJSONCopy } from '@/lib/general-utils';
import { AddSavedBlockEnvironmentVariable } from '@/types/saved-blocks-types';
import { Dispatch } from 'vuex';
import { OpenProjectMutation } from '@/types/project-editor-types';
import { AddBlockArguments, AddSharedFileArguments, AddSharedFileLinkArguments } from '@/store/modules/project-view';
import { ProjectViewActions } from '@/constants/store-constants';
import { SavedBlockStatusCheckResult } from '@/types/api-types';

function validatePathHasLeadingSlash(apiPath: string) {
  const pathHead = apiPath.startsWith('/') ? '' : '/';
  return `${pathHead}${apiPath}`;
}

function validatePathTail(apiPath: string) {
  if (apiPath != '/' && apiPath.endsWith('/')) {
    return apiPath.slice(0, -1);
  }
  return apiPath;
}

export function validatePath(apiPath: string) {
  return validatePathTail(validatePathHasLeadingSlash(apiPath));
}

export function nopWrite() {
  // Does nothing on purpose
}

export function createNewBlock<K extends keyof BlockTypeToDefaultState>(
  blockType: K,
  name: string,
  blockToExtend?: WorkflowState
): WorkflowState {
  return {
    ...blockTypeToDefaultStateMapping[blockType](),
    name: name,
    ...blockToExtend,
    type: blockType,
    version: CURRENT_BLOCK_SCHEMA,
    id: uuid()
  };
}

export function createNewTransition(
  transitionType: WorkflowRelationshipType,
  fromNode: string,
  nextNode: string,
  expression: string
): WorkflowRelationship {
  return {
    node: fromNode,
    next: nextNode,
    type: transitionType,
    name: transitionType,
    expression: expression,
    id: uuid(),
    version: CURRENT_TRANSITION_SCHEMA
  };
}

export async function safelyDuplicateBlock(
  dispatch: Dispatch,
  projectConfig: ProjectConfig,
  block: WorkflowState,
  shared_files: WorkflowFile[],
  overrideEnvironmentVariables?: AddSavedBlockEnvironmentVariable[] | null
) {
  const duplicateOfProjectConfig = deepJSONCopy(projectConfig);
  const duplicateOfBlock = deepJSONCopy(block);

  if (duplicateOfBlock.type === WorkflowStateType.LAMBDA) {
    const duplicateLambdaBlock = duplicateOfBlock as LambdaWorkflowState;

    // Get a list of the IDs for the current environment variables
    const existingEnvVariableIds = Object.keys(duplicateLambdaBlock.environment_variables);

    // Create a new list of IDs for the block
    const newIds = existingEnvVariableIds.map(() => uuid());

    // Go through the existing env variable IDs and give them new IDs
    duplicateLambdaBlock.environment_variables = existingEnvVariableIds.reduce(
      (newEnvVars, oldId, index) => {
        const newId = newIds[index];

        // Look for any matching overrides
        const foundMatchingOverride =
          overrideEnvironmentVariables && overrideEnvironmentVariables.find(t => t.id === oldId);

        // If we have an override specified, flesh that out.
        const newValue: BlockEnvironmentVariable = !foundMatchingOverride
          ? duplicateLambdaBlock.environment_variables[oldId]
          : {
              required: foundMatchingOverride.required,
              description: foundMatchingOverride.description,
              name: foundMatchingOverride.name,
              original_id: foundMatchingOverride.original_id
            };

        // Replace the value under the new ID
        newEnvVars[newId] = {
          ...newValue,
          // This copy lets us associate environment variables later
          original_id: oldId
        };

        return newEnvVars;
      },
      {} as BlockEnvironmentVariableList
    );

    // Go through the project config and create new IDs for the environment variables, while preserving the values
    const newProjectConfigVars = existingEnvVariableIds.reduce(
      (newEnvVars, oldId, index) => {
        const newId = newIds[index];

        // Look for any matching overrides
        const foundMatchingOverride =
          overrideEnvironmentVariables && overrideEnvironmentVariables.find(t => t.id === oldId);

        // Override values take precedence
        const existingValue = foundMatchingOverride || duplicateOfProjectConfig.environment_variables[oldId];

        const newValue: ProjectConfigEnvironmentVariable = {
          value: existingValue && existingValue.value !== undefined ? existingValue.value : '',
          timestamp: Date.now()
        };

        newEnvVars[newId] = deepJSONCopy(newValue);

        return newEnvVars;
      },
      {} as ProjectEnvironmentVariableList
    );

    // Merge the new list of variables with the old one.
    duplicateOfProjectConfig.environment_variables = {
      ...duplicateOfProjectConfig.environment_variables,
      ...newProjectConfigVars
    };
  }

  const openProjectMutation: OpenProjectMutation = {
    config: duplicateOfProjectConfig,
    project: null,
    markAsDirty: true
  };

  const addBlockArgs: AddBlockArguments = {
    rawBlockType: duplicateOfBlock.type,
    selectAfterAdding: true,
    customBlockProperties: duplicateOfBlock
  };

  // Update the project config with any new block settings
  await dispatch(`project/${ProjectViewActions.updateProject}`, openProjectMutation, { root: true });

  // Add the new block to the project
  const newBlock = await dispatch(`project/${ProjectViewActions.addIndividualBlock}`, addBlockArgs, { root: true });

  // Add all of the shared files to the project
  const sharedFileAddPromises = shared_files.map(shared_file => {
    const addSharedFileArgs: AddSharedFileArguments = {
      name: shared_file.name,
      body: shared_file.body
    };
    return dispatch(`project/${ProjectViewActions.addSharedFile}`, addSharedFileArgs, { root: true });
  });
  const sharedFileAddResults = await Promise.all(sharedFileAddPromises);

  // Now add all the shared file links from the files to the block we've added
  const sharedFileLinkAddPromises = sharedFileAddResults.map(shared_file => {
    const addSharedFileLinkArgs: AddSharedFileLinkArguments = {
      file_id: shared_file.id,
      node: newBlock.id,
      path: ''
    };
    return dispatch(`project/${ProjectViewActions.addSharedFileLink}`, addSharedFileLinkArgs, { root: true });
  });

  await sharedFileLinkAddPromises;
}

// Creates a lookup of environment variables IDs from current ID -> original ID
export function associateBlockConfigVariables(block: LambdaWorkflowState) {
  return Object.keys(block.environment_variables).reduce(
    (newEnvVars, oldId) => {
      const currentVariable = block.environment_variables[oldId];

      const originalId = currentVariable && currentVariable.original_id;

      // Take the original block env variable ID and map that to the "original id"
      // This lets us pull in config when we update a saved block
      newEnvVars[oldId] = originalId ? originalId : oldId;

      return newEnvVars;
    },
    {} as { [key: string]: string }
  );
}

export function updateBlockWithNewSavedBlockVersion(
  block: WorkflowState,
  savedBlockStatus: SavedBlockStatusCheckResult
) {
  if (block.type !== savedBlockStatus.block_object.type) {
    debugger;
    throw new Error('Unable to update saved block -- block types have changed');
  }

  if (block.type !== WorkflowStateType.LAMBDA) {
    // TODO: Support updating blocks that aren't code blocks.
    throw new Error('Unable to update blocks that are not code blocks. TODO!');
  }

  const lambdaBlock = block as LambdaWorkflowState;
  const savedLambdaBlock = savedBlockStatus.block_object as LambdaWorkflowState;

  const envVariableLookup = associateBlockConfigVariables(lambdaBlock);

  const newEnvironmentVariables = Object.keys(lambdaBlock.environment_variables).reduce((newEnvVars, envVarId) => {
    const originalId = envVariableLookup[envVarId];
    const savedBlockEnvVariable = savedLambdaBlock.environment_variables[originalId];

    const blockName = lambdaBlock.environment_variables[envVarId].name;

    // Check if there are any variables with the same name
    const matchedByName = Object.keys(savedLambdaBlock.environment_variables).filter(id => {
      return savedLambdaBlock.environment_variables[id].name === blockName;
    });

    // Replace the version of our environment variable with the updated version from the saved block
    if (originalId && savedBlockEnvVariable) {
      newEnvVars[envVarId] = {
        ...savedBlockEnvVariable,
        original_id: originalId
      };
    } else if (matchedByName.length > 0) {
      // Maintain association by name
      newEnvVars[envVarId] = {
        ...savedLambdaBlock.environment_variables[matchedByName[0]],
        original_id: matchedByName[0]
      };
    }

    return newEnvVars;
  }, deepJSONCopy(lambdaBlock.environment_variables));

  // Goes through and checks if there were any new variables added. If so, we add them to the block.
  const addedEnvironmentVariables = Object.keys(savedLambdaBlock.environment_variables).reduce(
    (addedEnvVars, envVarId) => {
      const baseBlockEnvVarIds = Object.keys(lambdaBlock.environment_variables);

      const name = savedLambdaBlock.environment_variables[envVarId].name;

      // Do we already have a variable with this name?
      const hasMatchByName = baseBlockEnvVarIds.some(id => {
        return lambdaBlock.environment_variables[id].name === name;
      });

      // Do we already have a variable with this ID?
      const hasMatchById = baseBlockEnvVarIds.some(id => {
        return envVariableLookup[id] === envVarId;
      });

      // If neither matches, then create a new variables (and preserve the association with the block).
      if (!hasMatchByName && !hasMatchById) {
        const newId = uuid();
        addedEnvVars[newId] = {
          ...savedLambdaBlock.environment_variables[envVarId],
          original_id: envVarId
        };
      }

      return addedEnvVars;
    },
    {} as BlockEnvironmentVariableList
  );

  const newBlock: LambdaWorkflowState = {
    ...lambdaBlock,
    ...savedBlockStatus.block_object,
    name: lambdaBlock.name,
    id: lambdaBlock.id,
    environment_variables: {
      ...newEnvironmentVariables,
      ...addedEnvironmentVariables
    }
  };

  return newBlock;
}

// Replaces the IDs of environment variables with the original ID
export function replaceBlockConfigVariableIds(list: BlockEnvironmentVariableList, lookup: { [key: string]: string }) {
  return Object.keys(list).reduce(
    (output, id) => {
      const lookupMatch = lookup[id];

      const { original_id, ...rest } = list[id];

      output[lookupMatch] = {
        ...rest
      };

      return output;
    },
    {} as BlockEnvironmentVariableList
  );
}

export function createBlockDataForPublishedSavedBlock(
  block: LambdaWorkflowState,
  name: string,
  savedInputData?: string
): LambdaWorkflowState {
  const envVariableLookup = associateBlockConfigVariables(block);

  const replacedEnvVariables = replaceBlockConfigVariableIds(block.environment_variables, envVariableLookup);

  return {
    ...block,
    environment_variables: replacedEnvVariables,
    name: name,
    saved_input_data: savedInputData
  };
}
