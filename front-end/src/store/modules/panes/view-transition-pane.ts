import { Module } from 'vuex';
import { RootState } from '../../store-types';
import { SqsQueueWorkflowState, WorkflowRelationship, WorkflowRelationshipType } from '@/types/graph';
import { getTransitionDataById } from '@/utils/project-helpers';
import { ProjectViewActions, ProjectViewMutators } from '@/constants/store-constants';
import { createToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';
import { PANE_POSITION } from '@/types/project-editor-types';
import { ChangeTransitionArguments } from '@/store/modules/project-view';

// Enums
export enum ViewTransitionMutators {
  setSelectedEdge = 'setSelectedEdge'
}

export enum ViewTransitionActions {
  resetPaneState = 'resetPaneState',
  selectCurrentlySelectedDeploymentEdge = 'selectCurrentlySelectedDeploymentEdge',
  selectEdgeFromOpenDeployment = 'selectEdgeFromOpenDeployment'
}

// Types
export interface ViewTransitionPaneState {
  selectedEdge: WorkflowRelationship | null;
}

// Initial State
const moduleState: ViewTransitionPaneState = {
  selectedEdge: null
};

const ViewTransitionPaneModule: Module<ViewTransitionPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [ViewTransitionMutators.setSelectedEdge](state, edge) {
      state.selectedEdge = edge;
    }
  },
  actions: {
    /**
     * Resets the state of the pane back to it's default.
     * @param context
     */
    async [ViewTransitionActions.resetPaneState](context) {
      context.commit(ViewTransitionMutators.setSelectedEdge, null);
    },
    async [ViewTransitionActions.selectCurrentlySelectedDeploymentEdge](context) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment || !deploymentStore.selectedResource) {
        console.error('Attempted to open edit transition pane without loaded deployment or selected resource');
        return;
      }

      await context.dispatch(ViewTransitionActions.selectEdgeFromOpenDeployment, deploymentStore.selectedResource);
    },
    async [ViewTransitionActions.selectEdgeFromOpenDeployment](context, edgeId: string) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment) {
        console.error('Attempted to open edit transition pane without loaded deployment');
        return;
      }

      //await context.dispatch(ViewTransitionActions.resetPaneState);

      const edge = getTransitionDataById(deploymentStore.openedDeployment, edgeId);

      if (!edge) {
        console.error('Attempted to select unknown block in edit block pane');
        return;
      }

      context.commit(ViewTransitionMutators.setSelectedEdge, edge);
    }
  }
};

export default ViewTransitionPaneModule;
