import {Module} from 'vuex';
import {RootState} from '../../store-types';
import {
  SqsQueueWorkflowState, WorkflowRelationship, WorkflowRelationshipType,
} from '@/types/graph';
import {getTransitionDataById} from "@/utils/project-helpers";
import {ProjectViewActions, ProjectViewMutators} from "@/constants/store-constants";
import {createToast} from "@/utils/toasts-utils";
import {ToastVariant} from "@/types/toasts-types";
import {PANE_POSITION} from "@/types/project-editor-types";
import {ChangeTransitionArguments} from "@/store/modules/project-view";

// Enums
export enum EditTransitionMutators {
  setSelectedEdge = 'setSelectedEdge',
}

export enum EditTransitionActions {
  resetPaneState = 'resetPaneState',
  deleteTransition = 'deleteTransition',
  selectCurrentlySelectedProjectEdge = 'selectCurrentlySelectedProjectEdge',
  selectEdgeFromOpenProject = 'selectEdgeFromOpenProject',
  cancelAndResetBlock = 'cancelAndResetBlock',
  changeTransitionType = 'changeTransitionType'
}

// Types
export interface EditTransitionPaneState {
  selectedEdge: WorkflowRelationship | null;
}

// Initial State
const moduleState: EditTransitionPaneState = {
  selectedEdge: null,
};

const EditTransitionPaneModule: Module<EditTransitionPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [EditTransitionMutators.setSelectedEdge](state, edge) {
      state.selectedEdge = edge;
    },
  },
  actions: {
    /**
     * Resets the state of the pane back to it's default.
     * @param context
     */
    async [EditTransitionActions.resetPaneState](context) {
      context.commit(EditTransitionMutators.setSelectedEdge, null);
      await context.dispatch(`project/${ProjectViewActions.deselectResources}`, null,{root: true});
    },
    async [EditTransitionActions.cancelAndResetBlock](context) {
      // Reset this pane state
      await context.dispatch(EditTransitionActions.resetPaneState);

      // Close this pane
      await context.dispatch(`project/${ProjectViewActions.closePane}`, PANE_POSITION.right, {root: true});
    },
    async [EditTransitionActions.selectCurrentlySelectedProjectEdge](context) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject || !projectStore.selectedResource) {
        console.error('Attempted to open edit transition pane without loaded project or selected resource');
        return;
      }

      await context.dispatch(EditTransitionActions.selectEdgeFromOpenProject, projectStore.selectedResource);
    },
    async [EditTransitionActions.selectEdgeFromOpenProject](context, edgeId: string) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit transition pane without loaded project');
        return;
      }

      //await context.dispatch(EditTransitionActions.resetPaneState);

      const edge = getTransitionDataById(projectStore.openedProject, edgeId);

      if (!edge) {
        console.error('Attempted to select unknown block in edit block pane');
        return;
      }

      context.commit(EditTransitionMutators.setSelectedEdge, edge);
    },
    async [EditTransitionActions.deleteTransition](context) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit transition pane without loaded project');
        return;
      }

      if (!context.state.selectedEdge) {
        console.error('Unable to perform delete -- state is invalid of edited edge');
        return;
      }

      await context.dispatch(`project/${ProjectViewActions.deleteExistingTransition}`, context.state.selectedEdge, {
        root: true
      });

      await createToast(context.dispatch, {
        title: 'Transition deleted!',
        content: `Successfully deleted transition!`,
        variant: ToastVariant.success
      });

      // We need to close the pane and reset the state
      await context.dispatch(EditTransitionActions.cancelAndResetBlock);
    },
    async [EditTransitionActions.changeTransitionType](context, transitionType: WorkflowRelationshipType) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit transition pane without loaded project');
        return;
      }

      if (!context.state.selectedEdge) {
        console.error('Unable to perform delete -- state is invalid of edited edge');
        return;
      }

      const changeTransitionArguments: ChangeTransitionArguments = {
        "transition": context.state.selectedEdge,
        "transitionType": transitionType,
      }

      await context.dispatch(`project/${ProjectViewActions.changeExistingTransition}`, changeTransitionArguments, {
        root: true
      });

      // We need to close the pane and reset the state
      await context.dispatch(EditTransitionActions.cancelAndResetBlock);
    },
  }
}

export default EditTransitionPaneModule;
