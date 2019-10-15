import { Module } from 'vuex';
import { IfDropDownSelectionType, RootState } from '../../store-types';
import { WorkflowRelationship, WorkflowRelationshipType } from '@/types/graph';
import { getTransitionDataById } from '@/utils/project-helpers';
import { ProjectViewActions } from '@/constants/store-constants';
import { createToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';
import { PANE_POSITION } from '@/types/project-editor-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { ChangeTransitionArguments } from '@/store/modules/project-view';

// Enums
export enum EditTransitionMutators {
  resetState = 'resetState',

  setSelectedEdge = 'setSelectedEdge',

  setIfDropdownSelection = 'setIfDropdownSelection',
  setIfExpression = 'setIfExpression',
  setValidTransitions = 'setValidTransitions',

  setConfirmDiscardModalVisibility = 'setConfirmDiscardModalVisibility'
}

export enum EditTransitionActions {
  deleteTransition = 'deleteTransition',
  selectCurrentlySelectedProjectEdge = 'selectCurrentlySelectedProjectEdge',
  selectEdgeFromOpenProject = 'selectEdgeFromOpenProject',
  cancelAndResetBlock = 'cancelAndResetBlock',
  changeTransitionType = 'changeTransitionType',
  tryToClose = 'tryToClose'
}

// Types
export interface EditTransitionPaneState {
  selectedEdge: WorkflowRelationship | null;

  ifSelectDropdownValue: IfDropDownSelectionType | null;
  ifExpression: string;

  confirmDiscardModalVisibility: boolean;
}

// Initial State
const moduleState: EditTransitionPaneState = {
  selectedEdge: null,

  ifSelectDropdownValue: null,
  ifExpression: '',

  confirmDiscardModalVisibility: false
};

const EditTransitionPaneModule: Module<EditTransitionPaneState, RootState> = {
  namespaced: true,
  state: deepJSONCopy(moduleState),
  getters: {
    isStateDirty: (state, getters, rootState) => {
      if (!state.selectedEdge) {
        return false;
      }

      if (rootState.project.newTransitionTypeSpecifiedInEditFlow !== WorkflowRelationshipType.IF) {
        return false;
      }

      const edge = state.selectedEdge;

      // Check if the ifExpression was modified
      return edge.expression !== rootState.project.ifExpression;
    }
  },
  mutations: {
    /**
     * Resets the state of the pane back to it's default.
     */
    [EditTransitionMutators.resetState](state) {
      resetStoreState(state, moduleState);
    },
    [EditTransitionMutators.setSelectedEdge](state, edge) {
      state.selectedEdge = edge;
    },
    [EditTransitionMutators.setConfirmDiscardModalVisibility](state, visibility) {
      state.confirmDiscardModalVisibility = visibility;
    }

    // TODO: Finish implementing this functionality here.
    // [ProjectViewMutators.setIfDropdownSelection](state, dropdownSelection: IfDropDownSelectionType) {
    //   state.ifSelectDropdownValue = dropdownSelection;
    // },
    // [ProjectViewMutators.setIfExpression](state, ifExpression: string) {
    //   state.ifExpression = ifExpression;
    // },
    // [ProjectViewMutators.setValidTransitions](state, node: WorkflowState) {
    //   if (!node || !state.openedProject) {
    //     state.availableTransitions = null;
    //     return;
    //   }
    //
    //   // Assigning this in a mutator because this algorithm is O(n^2) and that feels bad in a getter
    //   state.availableTransitions = getValidTransitionsForNode(state.openedProject, node);
    // },
  },
  actions: {
    async [EditTransitionActions.cancelAndResetBlock](context) {
      // Reset this pane state
      await context.commit(EditTransitionMutators.resetState);

      // Close this pane
      await context.dispatch(`project/${ProjectViewActions.closePane}`, PANE_POSITION.right, { root: true });
    },
    async [EditTransitionActions.tryToClose](context) {
      // We don't have a selected node, so we don't need to do anything.
      if (!context.state.selectedEdge) {
        return;
      }

      // If we have changes that we are going to discard, then ask the user to confirm destruction.
      if (context.getters.isStateDirty) {
        context.commit(EditTransitionMutators.setConfirmDiscardModalVisibility, true);
        return;
      }

      // Otherwise, close the pane!
      await context.dispatch(EditTransitionActions.cancelAndResetBlock);
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
        console.error('Unable to perform transition change -- state is invalid of edited edge');
        return;
      }

      const changeTransitionArguments: ChangeTransitionArguments = {
        transition: context.state.selectedEdge,
        transitionType: transitionType
      };

      await context.dispatch(`project/${ProjectViewActions.changeExistingTransition}`, changeTransitionArguments, {
        root: true
      });

      // We need to close the pane and reset the state
      await context.dispatch(EditTransitionActions.cancelAndResetBlock);
    }
  }
};

export default EditTransitionPaneModule;
