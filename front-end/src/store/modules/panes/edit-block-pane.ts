import Vue from 'vue';
import {Module} from 'vuex';
import {RootState} from '../../store-types';
import {LambdaWorkflowState, WorkflowState, WorkflowStateType} from '@/types/graph';
import {getNodeDataById} from '@/utils/project-helpers';

// Enums
export enum EditBlockMutators {
  setSelectedNode = 'setSelectedNode',
  
  // Inputs
  setBlockName = 'setBlockName',
  
  // Code Block Inputs
  setCodeLanguage = 'setCodeLanguage',
  setDependencyImports = 'setDependencyImports',
  setCodeInput = 'setCodeInput',
  setExecutionMemory = 'setExecutionMemory',
  setMaxExecutionTime = 'setMaxExecutionTime',
  setLayers = 'setLayers',
  setCodeModalVisibility = 'setCodeModalVisibility'
}

export enum EditBlockActions {
  selectNodeFromOpenProject = 'selectNodeFromOpenProject',
  selectCurrentlySelectedProjectNode = 'selectCurrentlySelectedProjectNode',
  
  // Shared Actions
  saveBlock = 'saveBlock',
  resetBlock = 'resetBlock',
  duplicateBlock = 'duplicateBlock',
  
  // Code Block specific
  saveCodeBlockToDatabase = 'saveCodeBlockToDatabase'
}

// Types
export interface EditBlockPaneState {
  selectedNode: WorkflowState | null,
  showCodeModal: boolean
}

// Initial State
const moduleState: EditBlockPaneState = {
  selectedNode: null,
  showCodeModal: false
};

function modifyBlock<T extends WorkflowState>(state: EditBlockPaneState, fn: (block: T) => void) {
  const block = state.selectedNode as T;
  fn(block);
  state.selectedNode = Object.assign({}, block);
}

function getBlockAsType<T extends WorkflowState>(state: EditBlockPaneState, type: WorkflowStateType, fn: (block: T) => void) {
  if (!state.selectedNode || state.selectedNode.type !== type) {
    return null;
  }
  modifyBlock<T>(state, fn);
}

function lambdaChange(state: EditBlockPaneState, fn: (block: LambdaWorkflowState) => void) {
  getBlockAsType<LambdaWorkflowState>(
    state,
    WorkflowStateType.LAMBDA,
    fn
  );
}

const EditBlockPaneModule: Module<EditBlockPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {
  
  },
  mutations: {
    [EditBlockMutators.setSelectedNode](state, node) {
      state.selectedNode = node;
    },
    
    // Shared mutations
    [EditBlockMutators.setBlockName](state, name) {
      modifyBlock(state, block => block.name = name);
    },
    
    // Code Block specific mutations
    [EditBlockMutators.setCodeInput](state, code) {
      lambdaChange(state, block => block.code = code);
    },
    [EditBlockMutators.setCodeLanguage](state, language) {
      lambdaChange(state, block => block.language = language);
    },
    [EditBlockMutators.setDependencyImports](state, libraries) {
      lambdaChange(state, block => block.libraries = libraries);
    },
    [EditBlockMutators.setMaxExecutionTime](state, maxExecTime) {
      lambdaChange(state, block => block.max_execution_time = parseInt(maxExecTime, 10));
    },
    [EditBlockMutators.setExecutionMemory](state, memory) {
      memory = Math.min(memory, 3072);
      memory = Math.max(memory, 128);
      
      lambdaChange(state, block => block.memory = memory);
    },
    [EditBlockMutators.setLayers](state, layers) {
      lambdaChange(state, block => block.layers = layers);
    },
    [EditBlockMutators.setCodeModalVisibility](state, visible) {
      state.showCodeModal = visible;
    }
  },
  actions: {
    async [EditBlockActions.selectNodeFromOpenProject](context, nodeId: string) {
      const projectStore = context.rootState.project;
      
      if (!projectStore.openedProject) {
        console.error('Attempted to open edit block pane without loaded project');
        return;
      }
      
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
        console.error('Attempted to open edit block pane without loaded project or selected resource');
        return;
      }
      
      await context.dispatch(EditBlockActions.selectNodeFromOpenProject, projectStore.selectedResource);
    }
  }
};

export default EditBlockPaneModule;