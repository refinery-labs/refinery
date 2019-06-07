import { Module } from 'vuex';
import { RootState } from '../../store-types';
import {
  LambdaWorkflowState,
  ScheduleTriggerWorkflowState,
  SnsTopicWorkflowState,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { getNodeDataById } from '@/utils/project-helpers';
import { createToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';
import { ProjectViewActions } from '@/constants/store-constants';
import { PANE_POSITION } from '@/types/project-editor-types';
import { DEFAULT_LANGUAGE_CODE } from '@/constants/project-editor-constants';
import { EditTopicBlock } from '@/components/ProjectEditor/EditBlockPane';

// Enums
export enum EditBlockMutators {
  setSelectedNode = 'setSelectedNode',
  setDirtyState = 'setDirtyState',

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

  // Timer Block Inputs
  setScheduleExpression = 'setScheduleExpression',
  setInputData = 'setInputData'
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

  // Code Block specific
  saveCodeBlockToDatabase = 'saveCodeBlockToDatabase'
}

// Types
export interface EditBlockPaneState {
  selectedNode: WorkflowState | null;
  confirmDiscardModalVisibility: false;
  showCodeModal: boolean;
  isStateDirty: boolean;
  wideMode: boolean;
}

// Initial State
const moduleState: EditBlockPaneState = {
  selectedNode: null,
  confirmDiscardModalVisibility: false,
  showCodeModal: false,
  isStateDirty: false,
  wideMode: false
};

function modifyBlock<T extends WorkflowState>(
  state: EditBlockPaneState,
  fn: (block: T) => void
) {
  const block = state.selectedNode as T;
  fn(block);
  state.isStateDirty = true;
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

function lambdaChange(
  state: EditBlockPaneState,
  fn: (block: LambdaWorkflowState) => void
) {
  getBlockAsType<LambdaWorkflowState>(state, WorkflowStateType.LAMBDA, fn);
}

function scheduleExpressionChange(
  state: EditBlockPaneState,
  fn: (block: ScheduleTriggerWorkflowState) => void
) {
  getBlockAsType<ScheduleTriggerWorkflowState>(
    state,
    WorkflowStateType.SCHEDULE_TRIGGER,
    fn
  );
}

function topicChange(
  state: EditBlockPaneState,
  fn: (block: SnsTopicWorkflowState) => void
) {
  getBlockAsType<SnsTopicWorkflowState>(state, WorkflowStateType.SNS_TOPIC, fn);
}

const EditBlockPaneModule: Module<EditBlockPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [EditBlockMutators.setSelectedNode](state, node) {
      state.selectedNode = node;
    },
    [EditBlockMutators.setDirtyState](state, dirtyState) {
      state.isStateDirty = dirtyState;
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
    [EditBlockMutators.setMaxExecutionTime](state, maxExecTime) {
      lambdaChange(
        state,
        block => (block.max_execution_time = parseInt(maxExecTime, 10))
      );
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
      scheduleExpressionChange(
        state,
        block => (block.schedule_expression = expression)
      );
    },
    [EditBlockMutators.setInputData](state, input_string: string) {
      scheduleExpressionChange(
        state,
        block => (block.input_string = input_string)
      );
    },
    [EditBlockMutators.setWidePanel](state, wide) {
      state.wideMode = wide;
    }
  },
  actions: {
    /**
     * Resets the state of the pane back to it's default.
     * @param context
     */
    async [EditBlockActions.resetPaneState](context) {
      context.commit(EditBlockMutators.setSelectedNode, null);
      context.commit(EditBlockMutators.setDirtyState, false);
      context.commit(EditBlockMutators.setCodeModalVisibility, false);
    },
    async [EditBlockActions.selectNodeFromOpenProject](
      context,
      nodeId: string
    ) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error(
          'Attempted to open edit block pane without loaded project'
        );
        return;
      }

      await context.dispatch(EditBlockActions.resetPaneState);

      const node = getNodeDataById(projectStore.openedProject, nodeId);

      if (!node) {
        console.error('Attempted to select unknown block in edit block pane');
        return;
      }

      context.commit(EditBlockMutators.setSelectedNode, node);
    },
    async [EditBlockActions.selectCurrentlySelectedProjectNode](context) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject || !projectStore.selectedResource) {
        console.error(
          'Attempted to open edit block pane without loaded project or selected resource'
        );
        return;
      }

      await context.dispatch(
        EditBlockActions.selectNodeFromOpenProject,
        projectStore.selectedResource
      );
    },
    async [EditBlockActions.saveBlock](context) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error(
          'Attempted to open edit block pane without loaded project'
        );
        return;
      }

      if (!context.state.isStateDirty || !context.state.selectedNode) {
        console.error(
          'Unable to perform save -- state is invalid of edited block'
        );
        return;
      }

      await context.dispatch(
        `project/${ProjectViewActions.updateExistingBlock}`,
        context.state.selectedNode,
        { root: true }
      );
      context.commit(EditBlockMutators.setDirtyState, false);

      await createToast(context.dispatch, {
        title: 'Block saved!',
        content: `Successfully saved changes to block with name: ${
          context.state.selectedNode.name
        }`,
        variant: ToastVariant.success
      });
    },
    async [EditBlockActions.tryToCloseBlock](context) {
      // If we have changes that we are going to discard, then ask the user to confirm destruction.
      if (context.state.isStateDirty) {
        context.commit(
          EditBlockMutators.setConfirmDiscardModalVisibility,
          true
        );
        return;
      }

      // Otherwise, close the pane!
      await context.dispatch(EditBlockActions.cancelAndResetBlock);
    },
    async [EditBlockActions.cancelAndResetBlock](context) {
      // Reset this pane state
      await context.dispatch(EditBlockActions.resetPaneState);

      // Close this pane
      await context.dispatch(
        `project/${ProjectViewActions.closePane}`,
        PANE_POSITION.right,
        { root: true }
      );
    }
  }
};

export default EditBlockPaneModule;
