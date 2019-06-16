import {Module} from 'vuex';
import {RootState} from '../../store-types';
import {
  WorkflowState,
} from '@/types/graph';
import {getNodeDataById, getTransitionsForNode} from '@/utils/project-helpers';

// Enums
export enum ViewBlockMutators {
  setSelectedNode = 'setSelectedNode',
  setCodeModalVisibility = 'setCodeModalVisibility',
  setLibrariesModalVisibility = 'setLibrariesModalVisibility',

  setWidePanel = 'setWidePanel'
}

export enum ViewBlockActions {
  selectNodeFromOpenProject = 'selectNodeFromOpenProject',
  selectCurrentlySelectedProjectNode = 'selectCurrentlySelectedProjectNode',
  resetPaneState = 'resetPaneState'
}

// Types
export interface ViewBlockPaneState {
  selectedNode: WorkflowState | null;
  showCodeModal: boolean;
  wideMode: boolean;

  // This doesn't really make sense here
  // but neither does having it in a selectedNode...
  librariesModalVisibility: boolean;
}

// Initial State
const moduleState: ViewBlockPaneState = {
  selectedNode: null,
  showCodeModal: false,
  wideMode: false,
  librariesModalVisibility: false,
};

const ViewBlockPaneModule: Module<ViewBlockPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [ViewBlockMutators.setSelectedNode](state, node) {
      state.selectedNode = node;
    },
    [ViewBlockMutators.setWidePanel](state, wide) {
      state.wideMode = wide;
    },
    [ViewBlockMutators.setLibrariesModalVisibility](state, visibility) {
      state.librariesModalVisibility = visibility;
    },
    [ViewBlockMutators.setCodeModalVisibility](state, visible) {
      state.showCodeModal = visible;
    },
  },
  actions: {
    /**
     * Resets the state of the pane back to it's default.
     * @param context
     */
    async [ViewBlockActions.resetPaneState](context) {
      context.commit(ViewBlockMutators.setSelectedNode, null);
      context.commit(ViewBlockMutators.setCodeModalVisibility, false);
    },
    async [ViewBlockActions.selectNodeFromOpenProject](context, nodeId: string) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment) {
        console.error('Attempted to open edit block pane without loaded project');
        return;
      }

      await context.dispatch(ViewBlockActions.resetPaneState);

      const node = getNodeDataById(deploymentStore.openedDeployment, nodeId);

      if (!node) {
        console.error('Attempted to select unknown block in edit block pane');
        return;
      }

      context.commit(ViewBlockMutators.setSelectedNode, node);
    },
    async [ViewBlockActions.selectCurrentlySelectedProjectNode](context) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment || !deploymentStore.selectedResource) {
        console.error('Attempted to open edit block pane without loaded project or selected resource');
        return;
      }

      await context.dispatch(ViewBlockActions.selectNodeFromOpenProject, deploymentStore.selectedResource);
    }
  }
};

export default ViewBlockPaneModule;
