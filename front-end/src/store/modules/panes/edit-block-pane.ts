import { Module } from 'vuex';
import deepEqual from 'fast-deep-equal';
import { RootState } from '../../store-types';
import {
  ApiEndpointWorkflowState,
  LambdaWorkflowState,
  ScheduleTriggerWorkflowState,
  SqsQueueWorkflowState,
  WorkflowRelationship,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { getNodeDataById, getTransitionsForNode } from '@/utils/project-helpers';
import { ProjectViewActions } from '@/constants/store-constants';
import { PANE_POSITION } from '@/types/project-editor-types';
import { DEFAULT_LANGUAGE_CODE } from '@/constants/project-editor-constants';
import { HTTP_METHOD } from '@/constants/api-constants';
import { validatePath } from '@/utils/block-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { getSavedBlockStatus } from '@/store/fetchers/api-helpers';
import { SavedBlockStatusCheckResult } from '@/types/api-types';

// Enums
export enum EditBlockMutators {
  resetState = 'resetState',

  setSelectedNode = 'setSelectedNode',
  setSelectedNodeOriginal = 'setSelectedNodeOriginal',
  setSelectedNodeMetadata = 'setSelectedNodeMetadata',
  setIsLoadingMetadata = 'setIsLoadingMetadata',

  setConfirmDiscardModalVisibility = 'setConfirmDiscardModalVisibility',
  setWidePanel = 'setWidePanel',

  // Inputs
  setBlockName = 'setBlockName',

  // Code Block Inputs
  setCodeLanguage = 'setCodeLanguage',
  setDependencyImports = 'setDependencyImports',
  setCodeInput = 'setCodeInput',
  setExecutionMemory = 'setExecutionMemory',
  setMaxExecutionTime = 'setMaxExecutionTime',
  setLayers = 'setLayers',
  setEnvironmentVariables = 'setEnvironmentVariables',
  setSavedInputData = 'setSavedInputData',

  setCodeModalVisibility = 'setCodeModalVisibility',
  setLibrariesModalVisibility = 'setLibrariesModalVisibility',

  setEnteredLibrary = 'setEnteredLibrary',
  deleteDependencyImport = 'deleteDependencyImport',
  addDependencyImport = 'addDependencyImport',

  // Timer Block Inputs
  setScheduleExpression = 'setScheduleExpression',
  setInputData = 'setInputData',

  // Queue Block Inputs
  setBatchSize = 'setBatchSize',

  // API Endpoint Inputs
  setHTTPMethod = 'setHTTPMethod',
  setHTTPPath = 'setHTTPPath'
}

export enum EditBlockActions {
  selectNodeFromOpenProject = 'selectNodeFromOpenProject',
  selectCurrentlySelectedProjectNode = 'selectCurrentlySelectedProjectNode',

  // Shared Actions
  saveBlock = 'saveBlock',
  tryToCloseBlock = 'tryToCloseBlock',
  cancelAndResetBlock = 'cancelAndResetBlock',
  duplicateBlock = 'duplicateBlock',
  deleteBlock = 'deleteBlock',
  deleteTransition = 'deleteTransition',
  // Code Block specific
  saveCodeBlockToDatabase = 'saveCodeBlockToDatabase',
  saveInputData = 'saveInputData'
}

export enum EditBlockGetters {
  isStateDirty = 'isStateDirty',
  isEditedBlockValid = 'isEditedBlockValid',
  collidingApiEndpointBlocks = 'collidingApiEndpointBlocks',
  isApiEndpointPathValid = 'isApiEndpointPathValid'
}

// Types
export interface EditBlockPaneState {
  selectedNode: WorkflowState | null;
  selectedNodeOriginal: WorkflowState | null;

  selectedNodeMetadata: SavedBlockStatusCheckResult | null;
  isLoadingMetadata: boolean;

  confirmDiscardModalVisibility: false;
  showCodeModal: boolean;
  wideMode: boolean;

  // This doesn't really make sense here
  // but neither does having it in a selectedNode...
  librariesModalVisibility: boolean;
  enteredLibrary: string;
}

// Initial State
const moduleState: EditBlockPaneState = {
  selectedNode: null,
  selectedNodeOriginal: null,
  selectedNodeMetadata: null,
  isLoadingMetadata: false,

  confirmDiscardModalVisibility: false,
  showCodeModal: false,
  wideMode: false,
  librariesModalVisibility: false,
  enteredLibrary: ''
};

function modifyBlock<T extends WorkflowState>(state: EditBlockPaneState, fn: (block: T) => void) {
  const block = state.selectedNode as T;
  fn(block);
  state.selectedNode = Object.assign({}, block);
}

function getBlockAsType<T extends WorkflowState>(
  state: EditBlockPaneState,
  type: WorkflowStateType,
  fn: (block: T) => void
) {
  if (!state.selectedNode || state.selectedNode.type !== type) {
    return null;
  }
  modifyBlock<T>(state, fn);
}

function lambdaChange(state: EditBlockPaneState, fn: (block: LambdaWorkflowState) => void) {
  getBlockAsType<LambdaWorkflowState>(state, WorkflowStateType.LAMBDA, fn);
}

function scheduleExpressionChange(state: EditBlockPaneState, fn: (block: ScheduleTriggerWorkflowState) => void) {
  getBlockAsType<ScheduleTriggerWorkflowState>(state, WorkflowStateType.SCHEDULE_TRIGGER, fn);
}

function sqsQueueChange(state: EditBlockPaneState, fn: (block: SqsQueueWorkflowState) => void) {
  getBlockAsType<SqsQueueWorkflowState>(state, WorkflowStateType.SQS_QUEUE, fn);
}

function apiEndpointChange(state: EditBlockPaneState, fn: (block: ApiEndpointWorkflowState) => void) {
  getBlockAsType<ApiEndpointWorkflowState>(state, WorkflowStateType.API_ENDPOINT, fn);
}

const EditBlockPaneModule: Module<EditBlockPaneState, RootState> = {
  namespaced: true,
  state: deepJSONCopy(moduleState),
  getters: {
    [EditBlockGetters.isStateDirty]: state =>
      state.selectedNode && state.selectedNodeOriginal && !deepEqual(state.selectedNode, state.selectedNodeOriginal),
    [EditBlockGetters.isEditedBlockValid]: (state, getters) => {
      if (!state.selectedNode) {
        return true;
      }

      if (state.selectedNode.type === WorkflowStateType.API_ENDPOINT) {
        // Not a huge fan of this being here...
        // But this prevents painful server issues from existing so it feels like the best move.
        const collidingBlocks = getters[EditBlockGetters.collidingApiEndpointBlocks];

        const validApiEndpointConfig = !collidingBlocks || collidingBlocks.length === 0;

        return validApiEndpointConfig && getters[EditBlockGetters.isApiEndpointPathValid];
      }

      return true;
    },
    [EditBlockGetters.collidingApiEndpointBlocks]: (state, getters, rootState) => {
      if (
        !rootState.project.openedProject ||
        !state.selectedNode ||
        state.selectedNode.type !== WorkflowStateType.API_ENDPOINT
      ) {
        return null;
      }

      const selectedNode = state.selectedNode as ApiEndpointWorkflowState;

      return rootState.project.openedProject.workflow_states
        .filter(w => w.type === WorkflowStateType.API_ENDPOINT)
        .filter(w => w.id !== selectedNode.id)
        .filter(w => {
          const apiW = w as ApiEndpointWorkflowState;
          // If both of these match, we have an invalid ApiEndpoint configuration
          return apiW.api_path === selectedNode.api_path && apiW.http_method === selectedNode.http_method;
        });
    },
    [EditBlockGetters.isApiEndpointPathValid]: state => {
      if (!state.selectedNode || state.selectedNode.type !== WorkflowStateType.API_ENDPOINT) {
        return true;
      }
      // If we have invalid characters, this will return false.
      return /^\/[a-zA-Z0-9/]*$/.test((state.selectedNode as ApiEndpointWorkflowState).api_path);
    }
  },
  mutations: {
    /**
     * Resets the state of the pane back to it's default.
     */
    [EditBlockMutators.resetState](state) {
      resetStoreState(state, moduleState);
    },
    [EditBlockMutators.setSelectedNode](state, node) {
      state.selectedNode = deepJSONCopy(node);
    },
    [EditBlockMutators.setSelectedNodeOriginal](state, node) {
      state.selectedNodeOriginal = deepJSONCopy(node);
    },
    [EditBlockMutators.setSelectedNodeMetadata](state, metadata) {
      state.selectedNodeMetadata = deepJSONCopy(metadata);
    },
    [EditBlockMutators.setIsLoadingMetadata](state, loading) {
      state.isLoadingMetadata = loading;
    },
    [EditBlockMutators.setConfirmDiscardModalVisibility](state, visibility) {
      state.confirmDiscardModalVisibility = visibility;
    },

    // Shared mutations
    [EditBlockMutators.setBlockName](state, name) {
      modifyBlock(state, block => (block.name = name));
    },

    // Code Block specific mutations
    [EditBlockMutators.setCodeInput](state, code) {
      lambdaChange(state, block => (block.code = code));
    },
    [EditBlockMutators.setCodeLanguage](state, language) {
      lambdaChange(state, block => {
        block.language = language;
        block.code = DEFAULT_LANGUAGE_CODE[block.language];
      });
    },
    [EditBlockMutators.setDependencyImports](state, libraries) {
      lambdaChange(state, block => (block.libraries = libraries));
    },
    [EditBlockMutators.deleteDependencyImport](state, library: string) {
      lambdaChange(state, block => {
        const newLibrariesArray = block.libraries.filter(existingLibrary => {
          return existingLibrary !== library;
        });
        block.libraries = newLibrariesArray;
      });
    },
    [EditBlockMutators.addDependencyImport](state, library: string) {
      lambdaChange(state, block => {
        const canonicalizedLibrary = library.trim();
        if (!block.libraries.includes(canonicalizedLibrary)) {
          const newLibrariesArray = deepJSONCopy(block.libraries).concat(canonicalizedLibrary);
          block.libraries = newLibrariesArray;
        }
      });
    },
    [EditBlockMutators.setMaxExecutionTime](state, maxExecTime) {
      lambdaChange(state, block => (block.max_execution_time = parseInt(maxExecTime, 10)));
    },
    [EditBlockMutators.setExecutionMemory](state, memory) {
      memory = Math.min(memory, 3072);
      memory = Math.max(memory, 128);

      lambdaChange(state, block => (block.memory = memory));
    },
    [EditBlockMutators.setSavedInputData](state, inputData) {
      lambdaChange(state, block => (block.saved_input_data = inputData));
    },
    [EditBlockMutators.setLayers](state, layers) {
      lambdaChange(state, block => (block.layers = layers));
    },
    [EditBlockMutators.setEnvironmentVariables](state, environmentVariables) {
      lambdaChange(state, block => (block.environment_variables = environmentVariables));
    },
    [EditBlockMutators.setCodeModalVisibility](state, visible) {
      state.showCodeModal = visible;
    },
    [EditBlockMutators.setScheduleExpression](state, expression: string) {
      scheduleExpressionChange(state, block => (block.schedule_expression = expression));
    },
    [EditBlockMutators.setInputData](state, input_string: string) {
      scheduleExpressionChange(state, block => (block.input_string = input_string));
    },
    [EditBlockMutators.setBatchSize](state, batch_size: number) {
      sqsQueueChange(state, block => (block.batch_size = batch_size));
    },
    [EditBlockMutators.setHTTPMethod](state, http_method: HTTP_METHOD) {
      apiEndpointChange(state, block => (block.http_method = http_method));
    },
    [EditBlockMutators.setHTTPPath](state, api_path: string) {
      apiEndpointChange(state, block => (block.api_path = validatePath(api_path)));
    },
    [EditBlockMutators.setWidePanel](state, wide) {
      state.wideMode = wide;
    },
    [EditBlockMutators.setLibrariesModalVisibility](state, visibility) {
      state.librariesModalVisibility = visibility;
    },
    [EditBlockMutators.setEnteredLibrary](state, libraryName: string) {
      state.enteredLibrary = libraryName;
    }
  },
  actions: {
    async [EditBlockActions.selectNodeFromOpenProject](context, nodeId: string) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit block pane without loaded project');
        return;
      }

      await context.commit(EditBlockMutators.resetState);

      const node = getNodeDataById(projectStore.openedProject, nodeId);

      if (!node) {
        console.error('Attempted to select unknown block in edit block pane');
        return;
      }

      context.commit(EditBlockMutators.setSelectedNode, node);
      context.commit(EditBlockMutators.setSelectedNodeOriginal, node);

      context.commit(EditBlockMutators.setIsLoadingMetadata, true);

      const savedBlockStatus = await getSavedBlockStatus(node);

      if (savedBlockStatus && context.state.selectedNode) {
        const hasNode = context.state.selectedNode;
        const nodeIdIsSameAsRequestId =
          context.state.selectedNode.saved_block_metadata &&
          context.state.selectedNode.saved_block_metadata.id === savedBlockStatus.id;

        // Check that we still have the same selected node as when this request went out...
        // On slow connections this check is important.
        if (hasNode && nodeIdIsSameAsRequestId) {
          context.commit(EditBlockMutators.setSelectedNodeMetadata, savedBlockStatus);
        }
      }

      context.commit(EditBlockMutators.setIsLoadingMetadata, false);
    },
    async [EditBlockActions.selectCurrentlySelectedProjectNode](context) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject || !projectStore.selectedResource) {
        console.error('Attempted to open edit block pane without loaded project or selected resource');
        return;
      }

      await context.dispatch(EditBlockActions.selectNodeFromOpenProject, projectStore.selectedResource);
    },
    async [EditBlockActions.saveBlock](context) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit block pane without loaded project');
        return;
      }

      const node = context.state.selectedNode;

      if (!node) {
        console.error('Missing selected node to save');
        return;
      }

      if (!context.getters.isEditedBlockValid) {
        throw new Error('State of block is invalid to save, aborting save');
      }

      if (!context.getters.isStateDirty) {
        return;
      }

      await context.dispatch(`project/${ProjectViewActions.updateExistingBlock}`, context.state.selectedNode, {
        root: true
      });

      // Set the "original" to the new block.
      context.commit(EditBlockMutators.setSelectedNodeOriginal, context.state.selectedNode);
    },
    async [EditBlockActions.deleteBlock](context) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit block pane without loaded project');
        return;
      }

      if (!context.state.selectedNode) {
        console.error('Unable to perform delete -- state is invalid of edited block');
        return;
      }

      // The array of transitions we need to delete
      const transitions_to_delete: WorkflowRelationship[] = getTransitionsForNode(
        projectStore.openedProject,
        context.state.selectedNode
      );

      // Dispatch an action to delete all of them.
      await Promise.all(
        transitions_to_delete.map(async transition => {
          await context.dispatch(`project/${ProjectViewActions.deleteExistingTransition}`, transition, {
            root: true
          });
        })
      );

      await context.dispatch(`project/${ProjectViewActions.deleteExistingBlock}`, context.state.selectedNode, {
        root: true
      });

      // We need to close the pane and reset the state
      await context.dispatch(EditBlockActions.cancelAndResetBlock);
    },
    async [EditBlockActions.tryToCloseBlock](context) {
      // We don't have a selected node, so we don't need to do anything.
      if (!context.state.selectedNode) {
        return;
      }

      // If we have changes that we are going to discard, then ask the user to confirm destruction.
      if (context.getters.isStateDirty) {
        context.commit(EditBlockMutators.setConfirmDiscardModalVisibility, true);
        return;
      }

      // Otherwise, close the pane!
      await context.dispatch(EditBlockActions.cancelAndResetBlock);
    },
    async [EditBlockActions.cancelAndResetBlock](context) {
      // Reset this pane state
      context.commit(EditBlockMutators.resetState);

      // Close this pane
      await context.dispatch(`project/${ProjectViewActions.closePane}`, PANE_POSITION.right, { root: true });
    }
  }
};

export default EditBlockPaneModule;
