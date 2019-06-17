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
import { createToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';
import { ProjectViewActions , ProjectViewMutators} from '@/constants/store-constants';
import { PANE_POSITION } from '@/types/project-editor-types';
import { DEFAULT_LANGUAGE_CODE } from '@/constants/project-editor-constants';
import { API_ENDPOINT, HTTP_METHOD } from '@/constants/api-constants';
import { validatePath } from '@/utils/block-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import {
  GetBuildStatusRequest,
  GetBuildStatusResponse,
  StartLibraryBuildRequest,
  StartLibraryBuildResponse
} from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';

// Enums
export enum EditBlockMutators {
  setSelectedNode = 'setSelectedNode',
  setSelectedNodeOriginal = 'setSelectedNodeOriginal',

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
  resetPaneState = 'resetPaneState',

  // Shared Actions
  saveBlock = 'saveBlock',
  tryToCloseBlock = 'tryToCloseBlock',
  cancelAndResetBlock = 'cancelAndResetBlock',
  duplicateBlock = 'duplicateBlock',
  deleteBlock = 'deleteBlock',
  deleteTransition = 'deleteTransition',
  // Code Block specific
  saveCodeBlockToDatabase = 'saveCodeBlockToDatabase',
  checkBuildStatus = 'checkBuildStatus',
  StartLibraryBuild = 'StartLibraryBuild'
}

// Types
export interface EditBlockPaneState {
  selectedNode: WorkflowState | null;
  selectedNodeOriginal: WorkflowState | null;
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
  state: moduleState,
  getters: {
    isStateDirty: state =>
      state.selectedNode && state.selectedNodeOriginal && !deepEqual(state.selectedNode, state.selectedNodeOriginal)
  },
  mutations: {
    [EditBlockMutators.setSelectedNode](state, node) {
      state.selectedNode = node;
    },
    [EditBlockMutators.setSelectedNodeOriginal](state, node) {
      state.selectedNodeOriginal = deepJSONCopy(node);
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
    [EditBlockMutators.setLayers](state, layers) {
      lambdaChange(state, block => (block.layers = layers));
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
    /**
     * Resets the state of the pane back to it's default.
     * @param context
     */
    async [EditBlockActions.resetPaneState](context) {
      context.commit(EditBlockMutators.setSelectedNode, null);
      context.commit(EditBlockMutators.setSelectedNodeOriginal, null);
      context.commit(EditBlockMutators.setCodeModalVisibility, false);
      context.commit(EditBlockMutators.setConfirmDiscardModalVisibility, false);
    },
    async [EditBlockActions.selectNodeFromOpenProject](context, nodeId: string) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit block pane without loaded project');
        return;
      }

      await context.dispatch(EditBlockActions.resetPaneState);

      const node = getNodeDataById(projectStore.openedProject, nodeId);

      if (!node) {
        console.error('Attempted to select unknown block in edit block pane');
        return;
      }

      context.commit(EditBlockMutators.setSelectedNode, node);
      context.commit(EditBlockMutators.setSelectedNodeOriginal, node);
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

      if (!context.getters.isStateDirty || !context.state.selectedNode) {
        console.error('Unable to perform save -- state is invalid of edited block');
        return;
      }

      await context.dispatch(`project/${ProjectViewActions.updateExistingBlock}`, context.state.selectedNode, {
        root: true
      });

      // Set the "original" to the new block.
      context.commit(EditBlockMutators.setSelectedNodeOriginal, context.state.selectedNode);

      await createToast(context.dispatch, {
        title: 'Block saved!',
        content: `Successfully saved changes to block with name: ${context.state.selectedNode.name}`,
        variant: ToastVariant.success
      });
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

      await createToast(context.dispatch, {
        title: 'Block deleted!',
        content: `Successfully deleted block with name: ${context.state.selectedNode.name}`,
        variant: ToastVariant.success
      });

      // We need to close the pane and reset the state
      await context.dispatch(EditBlockActions.cancelAndResetBlock);
    },
    async [EditBlockActions.tryToCloseBlock](context) {
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
      await context.dispatch(EditBlockActions.resetPaneState);

      // Close this pane
      await context.dispatch(`project/${ProjectViewActions.closePane}`, PANE_POSITION.right, { root: true });
    },
    async [EditBlockActions.checkBuildStatus](context) {
      if (context.state.selectedNode === null || context.state.selectedNode.type !== WorkflowStateType.LAMBDA) {
        console.error("Cannot kick off build for libraries because user doesn't have a node selected.");
        return;
      }

      const lambdaBlock = context.state.selectedNode as LambdaWorkflowState;

      const response = await makeApiRequest<GetBuildStatusRequest, GetBuildStatusResponse>(
        API_ENDPOINT.GetBuildStatus,
        {
          libraries: lambdaBlock.libraries,
          language: lambdaBlock.language
        }
      );

      if (!response || !response.success) {
        console.error('Unable to check library build cache: server error.');
        throw 'Server error occurred while checking library build cache!';
      }

      return response.is_already_cached;
    },
    async [EditBlockActions.StartLibraryBuild](context) {
      if (context.state.selectedNode === null || context.state.selectedNode.type !== WorkflowStateType.LAMBDA) {
        console.error("Cannot kick off build for libraries because user doesn't have a node selected.");
        return;
      }

      const lambdaBlock = context.state.selectedNode as LambdaWorkflowState;

      // Check if we're already build this before
      const buildIsCached = await context.dispatch(EditBlockActions.checkBuildStatus);

      // If so no need to kick it off
      if (buildIsCached) {
        return;
      }

      const response = await makeApiRequest<StartLibraryBuildRequest, StartLibraryBuildResponse>(
        API_ENDPOINT.StartLibraryBuild,
        {
          libraries: lambdaBlock.libraries,
          language: lambdaBlock.language
        }
      );

      if (!response || !response.success) {
        console.error('Unable kick off library build: server error.');
        throw 'Server error occurred while kicking off library build!';
      }
    }
  }
};

export default EditBlockPaneModule;
