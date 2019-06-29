import { Module } from 'vuex';
import { IfDropDownSelectionType, RootState } from '../../store-types';
import { SqsQueueWorkflowState, WorkflowRelationship, WorkflowRelationshipType, WorkflowState } from '@/types/graph';
import { getTransitionDataById, getValidTransitionsForNode } from '@/utils/project-helpers';
import { ProjectViewActions, ProjectViewMutators } from '@/constants/store-constants';
import { createToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';
import { PANE_POSITION } from '@/types/project-editor-types';
import { ChangeTransitionArguments } from '@/store/modules/project-view';
import deepEqual from 'fast-deep-equal';
import { deepJSONCopy } from '@/lib/general-utils';
import { EditBlockMutators } from '@/store/modules/panes/edit-block-pane';

// Enums
export enum EditTransitionMutators {
  setSelectedEdge = 'setSelectedEdge',
  setSelectedEdgeOriginal = 'setSelectedEdgeOriginal',

  setIfDropdownSelection = 'setIfDropdownSelection',
  setIfExpression = 'setIfExpression',
  setValidTransitions = 'setValidTransitions'
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
  selectedEdgeOriginal: WorkflowRelationship | null;

  ifSelectDropdownValue: IfDropDownSelectionType | null;
  ifExpression: string;
}

// Initial State
const moduleState: EditTransitionPaneState = {
  selectedEdge: null,
  selectedEdgeOriginal: null,

  ifSelectDropdownValue: null,
  ifExpression: ''
};

const EditTransitionPaneModule: Module<EditTransitionPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {
    isStateDirty: state =>
      state.selectedEdge && state.selectedEdgeOriginal && !deepEqual(state.selectedEdge, state.selectedEdgeOriginal)
  },
  mutations: {
    [EditTransitionMutators.setSelectedEdge](state, edge) {
      state.selectedEdge = edge;
    },
    [EditTransitionMutators.setSelectedEdgeOriginal](state, edge) {
      state.selectedEdgeOriginal = deepJSONCopy(edge);
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
    /**
     * Resets the state of the pane back to it's default.
     * @param context
     */
    async [EditTransitionActions.resetPaneState](context) {
      context.commit(EditTransitionMutators.setSelectedEdge, null);
      context.commit(EditTransitionMutators.setSelectedEdgeOriginal, null);
      await context.dispatch(`project/${ProjectViewActions.deselectResources}`, null, { root: true });
      // Close the panel since we're done.
      await context.dispatch(`project/${ProjectViewActions.closePane}`, PANE_POSITION.right, { root: true });
    },
    async [EditTransitionActions.cancelAndResetBlock](context) {
      // Reset this pane state
      await context.dispatch(EditTransitionActions.resetPaneState);

      // Close this pane
      await context.dispatch(`project/${ProjectViewActions.closePane}`, PANE_POSITION.right, { root: true });
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
      context.commit(EditTransitionMutators.setSelectedEdgeOriginal, edge);
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
