import uuid from 'uuid/v4';
import {
  BlockEnvironmentVariable,
  BlockEnvironmentVariableList,
  LambdaWorkflowState,
  ProjectConfig,
  ProjectConfigEnvironmentVariable,
  ProjectEnvironmentVariableList,
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
import { AddBlockArguments } from '@/store/modules/project-view';
import { ProjectViewActions } from '@/constants/store-constants';

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
  overrideEnvironmentVariables?: AddSavedBlockEnvironmentVariable[] | null
) {
  const duplicateOfProjectConfig = deepJSONCopy(projectConfig);
  const duplicateOfBlock = deepJSONCopy(block);

  if (duplicateOfBlock.type === WorkflowStateType.LAMBDA) {
    const lambdaBlock = duplicateOfBlock as LambdaWorkflowState;

    // Get a list of the IDs for the current environment variables
    const existingEnvVariableIds = Object.keys(lambdaBlock.environment_variables);

    // Create a new list of IDs for the block
    const newIds = existingEnvVariableIds.map(() => uuid());

    // Go through the existing env variable IDs and give them new IDs
    lambdaBlock.environment_variables = existingEnvVariableIds.reduce(
      (newEnvVars, oldId, index) => {
        const newId = newIds[index];

        // Look for any matching overrides
        const foundMatchingOverride =
          overrideEnvironmentVariables && overrideEnvironmentVariables.find(t => t.id === oldId);

        // If we have an override specified, flesh that out.
        const newValue: BlockEnvironmentVariable = !foundMatchingOverride
          ? lambdaBlock.environment_variables[oldId]
          : {
              required: foundMatchingOverride.required,
              description: foundMatchingOverride.description,
              name: foundMatchingOverride.name
            };

        // Replace the value under the new ID
        newEnvVars[newId] = newValue;

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
  await dispatch(`project/${ProjectViewActions.addIndividualBlock}`, addBlockArgs, { root: true });
}
