/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import uuid from 'uuid/v4';
import {ProjectViewState, RootState} from '@/store/store-types';
import {
  CyElements,
  CyStyle,
  ProjectConfig,
  RefineryProject,
  WorkflowRelationship,
  WorkflowRelationshipType,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import {generateCytoscapeElements, generateCytoscapeStyle} from '@/lib/refinery-to-cytoscript-converter';
import {LayoutOptions} from 'cytoscape';
import cytoscape from '@/components/CytoscapeGraph';
import {ProjectViewActions, ProjectViewMutators} from '@/constants/store-constants';
import {getApiClient} from '@/store/fetchers/refinery-api';
import {API_ENDPOINT} from '@/constants/api-constants';
import {
  GetProjectConfigRequest,
  GetProjectConfigResponse,
  GetSavedProjectRequest,
  GetSavedProjectResponse,
  SaveProjectRequest,
  SaveProjectResponse
} from '@/types/api-types';
import {
  OpenProjectMutation,
  PANE_POSITION,
  SIDEBAR_PANE,
  UpdateLeftSidebarPaneStateMutation
} from '@/types/project-editor-types';
import {
  getNodeDataById,
  getValidBlockToBlockTransitions,
  getValidTransitionsForNode,
  unwrapJson,
  unwrapProjectJson,
  wrapJson
} from '@/utils/project-helpers';
import {blockTypeToDefaultStateMapping, blockTypeToImageLookup} from '@/constants/project-editor-constants';
import EditBlockPaneModule, {EditBlockActions} from '@/store/modules/panes/edit-block-pane';
import {createToast} from '@/utils/toasts-utils';
import {ToastVariant} from '@/types/toasts-types';

interface AddBlockArguments {
  rawBlockType: string;
  selectAfterAdding: boolean,
}

const moduleState: ProjectViewState = {
  openedProject: null,
  openedProjectConfig: null,

  openedProjectOriginal: null,
  openedProjectConfigOriginal: null,

  isLoadingProject: true,
  isProjectBusy: false,
  hasProjectBeenModified: false,

  leftSidebarPaneState: {
    [SIDEBAR_PANE.addBlock]: {},
    [SIDEBAR_PANE.addTransition]: {},
    [SIDEBAR_PANE.allBlocks]: {},
    [SIDEBAR_PANE.allVersions]: {},
    [SIDEBAR_PANE.deployProject]: {},
    [SIDEBAR_PANE.saveProject]: {},
    [SIDEBAR_PANE.editBlock]: {},
    [SIDEBAR_PANE.editTransition]: {}
  },
  activeLeftSidebarPane: null,
  activeRightSidebarPane: null,

  // Shared Graph State
  selectedResource: null,
  // If this is "null" then it enables all elements
  enabledGraphElements: null,

  // Cytoscape Specific state
  cytoscapeElements: null,
  cytoscapeStyle: null,
  cytoscapeLayoutOptions: null,
  cytoscapeConfig: null,

  // Add New Block Pane
  selectedBlockIndex: null,

  // Add New Transition Pane
  isAddingTransitionCurrently: false,
  newTransitionTypeSpecifiedInAddFlow: null,
  availableTransitions: null
};

const ProjectViewModule: Module<ProjectViewState, RootState> = {
  namespaced: true,
  modules: {
    editBlockPane: EditBlockPaneModule
  },
  state: moduleState,
  getters: {
    transitionAddButtonEnabled: state => {
      if (!state.availableTransitions) {
        return false;
      }

      return state.availableTransitions.simple.length > 0 || state.availableTransitions.complex.length > 0;
    },
    /**
     * Returns the list of "next" valid blocks to select
     * @param state Vuex state object
     */
    getValidBlockToBlockTransitions: state => getValidBlockToBlockTransitions(state),
    /**
     * Returns which menu items are able to be displayed by the Add Transition pane
     * @param state Vuex state object
     */
    getValidMenuDisplayTransitionTypes: state => {
      if (!state.availableTransitions) {
        // Return an empty list because our state is invalid, but we also hate null types :)
        return [];
      }

      if (state.availableTransitions.complex.length > 0) {
        // Return every type as available
        return [
          WorkflowRelationshipType.IF,
          WorkflowRelationshipType.THEN,
          WorkflowRelationshipType.ELSE,
          WorkflowRelationshipType.EXCEPTION,
          WorkflowRelationshipType.FAN_OUT,
          WorkflowRelationshipType.FAN_IN
        ];
      }

      if (state.availableTransitions.simple.length > 0) {
        // Only return "then" being enabled
        return [WorkflowRelationshipType.THEN];
      }

      // There are no valid transitions available
      return [];
    },
    canSaveProject: state => state.hasProjectBeenModified && !state.isProjectBusy && !state.isAddingTransitionCurrently
  },
  mutations: {
    [ProjectViewMutators.setOpenedProject](state, project: RefineryProject) {
      state.openedProject = project;
    },
    [ProjectViewMutators.setOpenedProjectConfig](state, config: ProjectConfig) {
      state.openedProjectConfig = config;
    },
    [ProjectViewMutators.setOpenedProjectOriginal](state, project: RefineryProject) {
      state.openedProjectOriginal = unwrapJson<RefineryProject>(wrapJson(project));
    },
    [ProjectViewMutators.setOpenedProjectConfigOriginal](state, config: ProjectConfig) {
      state.openedProjectConfigOriginal = unwrapJson<ProjectConfig>(wrapJson(config));
    },

    [ProjectViewMutators.isLoadingProject](state, value: boolean) {
      state.isLoadingProject = value;
    },
    [ProjectViewMutators.isProjectBusy](state, value: boolean) {
      state.isProjectBusy = value;
    },
    [ProjectViewMutators.markProjectDirtyStatus](state, value: boolean) {
      state.hasProjectBeenModified = value;
    },
    [ProjectViewMutators.selectedResource](state, resourceId: string) {
      state.selectedResource = resourceId;
    },
    [ProjectViewMutators.setCytoscapeElements](state, elements: CyElements) {
      state.cytoscapeElements = elements;
    },
    [ProjectViewMutators.setCytoscapeStyle](state, stylesheet: CyStyle) {
      state.cytoscapeStyle = stylesheet;
    },
    [ProjectViewMutators.setCytoscapeLayout](state, layout: LayoutOptions) {
      state.cytoscapeLayoutOptions = layout;
    },
    [ProjectViewMutators.setCytoscapeConfig](state, config: cytoscape.CytoscapeOptions) {
      state.cytoscapeConfig = config;
    },

    // Pane Logic
    [ProjectViewMutators.setLeftSidebarPaneState](state, mutation: UpdateLeftSidebarPaneStateMutation) {
      state.leftSidebarPaneState[mutation.leftSidebarPane] = {
        ...state.leftSidebarPaneState[mutation.leftSidebarPane],
        ...mutation.newState
      };
    },
    [ProjectViewMutators.setLeftSidebarPane](state, leftSidebarPaneType: SIDEBAR_PANE | null) {
      state.activeLeftSidebarPane = leftSidebarPaneType;
    },
    [ProjectViewMutators.setRightSidebarPane](state, paneType: SIDEBAR_PANE | null) {
      state.activeRightSidebarPane = paneType;
    },

    // Add New Pane
    [ProjectViewMutators.setSelectedBlockIndex](state, selectedIndex: number | null) {
      state.selectedBlockIndex = selectedIndex;
    },

    // Add Transition Pane
    [ProjectViewMutators.setAddingTransitionStatus](state, addingCurrently: boolean) {
      state.isAddingTransitionCurrently = addingCurrently;
    },
    [ProjectViewMutators.setAddingTransitionType](state, transitionType: WorkflowRelationshipType | null) {
      state.newTransitionTypeSpecifiedInAddFlow = transitionType;
    },
    [ProjectViewMutators.setValidTransitions](state, node: WorkflowState) {
      if (!node || !state.openedProject) {
        state.availableTransitions = null;
        return;
      }

      // Assigning this in a mutator because this algorithm is O(n^2) and that feels bad in a getter
      state.availableTransitions = getValidTransitionsForNode(state.openedProject, node);
    }
  },
  actions: {
    async [ProjectViewActions.openProject](context, request: GetSavedProjectRequest) {
      context.commit(ProjectViewMutators.isLoadingProject, true);

      const getProjectClient = getApiClient(API_ENDPOINT.GetSavedProject);

      const projectResult = (await getProjectClient(request)) as GetSavedProjectResponse;

      if (!projectResult.success) {
        // TODO: Handle error gracefully
        console.error('Unable to open project, missing project');
        context.commit(ProjectViewMutators.isLoadingProject, false);
        return;
      }

      const project = unwrapProjectJson(projectResult);

      if (!project) {
        // TODO: Handle error gracefully
        console.error('Unable to read project from server');
        context.commit(ProjectViewMutators.isLoadingProject, false);
        return;
      }

      const getProjectConfigClient = getApiClient(API_ENDPOINT.GetProjectConfig);

      const getConfigRequest: GetProjectConfigRequest = {
        project_id: project.project_id
      };

      const projectConfigResult = (await getProjectConfigClient(getConfigRequest)) as GetProjectConfigResponse;

      if (!projectConfigResult || !projectConfigResult.success || !projectConfigResult.result) {
        // TODO: Handle error gracefully
        console.error('Unable to open project, missing config');
        return;
      }

      const projectConfig = projectConfigResult.result;

      if (!projectConfig) {
        console.error('Unable to deserialize project config');
        context.commit(ProjectViewMutators.isLoadingProject, false);
        return;
      }

      // Ensures that we have all fields, especially if the schema changes.
      project.workflow_states = project.workflow_states.map(wfs => ({
        ...blockTypeToDefaultStateMapping[wfs.type],
        ...wfs
      }));

      const params: OpenProjectMutation = {
        project: project,
        config: projectConfig,
        markAsDirty: false
      };

      await context.dispatch(ProjectViewActions.updateProject, params);

      context.commit(ProjectViewMutators.isLoadingProject, false);
    },
    async [ProjectViewActions.updateProject](context, params: OpenProjectMutation) {
      const elements = generateCytoscapeElements(params.project);

      const stylesheet = generateCytoscapeStyle();

      context.commit(ProjectViewMutators.setOpenedProject, params.project);

      if (params.config) {
        context.commit(ProjectViewMutators.setOpenedProjectConfig, params.config);
      }

      if (!params.markAsDirty) {
        context.commit(ProjectViewMutators.setOpenedProjectOriginal, params.project);
        context.commit(ProjectViewMutators.setOpenedProjectConfig, params.config);
      }

      // TODO: Make this actually compare IDs or something... But maybe we can hack it with Undo?
      context.commit(ProjectViewMutators.markProjectDirtyStatus, params.markAsDirty);

      context.commit(ProjectViewMutators.setCytoscapeElements, elements);
      context.commit(ProjectViewMutators.setCytoscapeStyle, stylesheet);
    },
    async [ProjectViewActions.saveProject](context) {
      if (!context.state.openedProject || !context.state.openedProjectConfig || !context.state.hasProjectBeenModified) {
        console.error('Project attempted to be saved but it was not in a valid state');
        return;
      }

      context.commit(ProjectViewMutators.isProjectBusy, true);

      const projectJson = wrapJson(context.state.openedProject);
      const configJson = wrapJson(context.state.openedProjectConfig);

      if (!projectJson || !configJson) {
        console.error('Unable to serialize project into JSON data');
        return;
      }

      const request: SaveProjectRequest = {
        diagram_data: projectJson,
        project_id: context.state.openedProject.project_id,
        config: configJson,
        // We can set this to false and let the backend bump versions for us. :)
        version: false // context.state.openedProjectConfig.version + 1
      };

      const saveProjectApiClient = getApiClient(API_ENDPOINT.SaveProject);

      const response = (await saveProjectApiClient(request)) as SaveProjectResponse;

      if (!response.success) {
        console.error('Unable to save project!');
        return;
      }

      const params: OpenProjectMutation = {
        project: {
          ...context.state.openedProject,
          // We need to sync the version against what the server has
          version: response.project_version || context.state.openedProject.version
        },
        config: context.state.openedProjectConfig,
        markAsDirty: false
      };

      await context.dispatch('updateProject', params);

      context.commit(ProjectViewMutators.isProjectBusy, true);
    },
    async [ProjectViewActions.clearSelection](context) {
      if (context.state.isAddingTransitionCurrently) {
        return;
      }

      context.commit(ProjectViewMutators.selectedResource, null);
      await context.dispatch('updateAvailableTransitions');
    },
    async [ProjectViewActions.selectNode](context, nodeId: string) {
      if (context.state.isAddingTransitionCurrently) {
        await context.dispatch('completeTransitionAdd', nodeId);
        return;
      }

      // TODO: Check if we currently have changes that we need to save in a panel...

      //await context.dispatch(ProjectViewActions.clearSelection);

      if (!context.state.openedProject) {
        console.error('Attempted to select node without opened project', nodeId);
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }

      const nodes = context.state.openedProject.workflow_states.filter(e => e.id === nodeId);

      if (nodes.length === 0) {
        console.error('No node was found with id', nodeId);
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }

      const node = nodes[0];

      context.commit(ProjectViewMutators.selectedResource, node.id);

      await context.dispatch(ProjectViewActions.updateAvailableTransitions);

      // Opens up the Edit block pane
      await context.dispatch(ProjectViewActions.openRightSidebarPane, SIDEBAR_PANE.editBlock);
      await context.dispatch(`editBlockPane/${EditBlockActions.selectCurrentlySelectedProjectNode}`);
    },
    async [ProjectViewActions.selectEdge](context, edgeId: string) {
      if (context.state.isAddingTransitionCurrently) {
        // TODO: Add a shake or something? Tell the user that it's bjorked.
        return;
      }

      // await context.dispatch(ProjectViewActions.clearSelection);

      if (!context.state.openedProject) {
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }

      const edges = context.state.openedProject.workflow_relationships.filter(e => e.id === edgeId);

      if (edges.length === 0) {
        console.error('No edge was found with id', edgeId);
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }

      context.commit(ProjectViewMutators.selectedResource, edges[0].id);

      await context.dispatch(ProjectViewActions.updateAvailableTransitions);
    },
    async [ProjectViewActions.completeTransitionAdd](context, nodeId: string) {
      if (!context.state.isAddingTransitionCurrently) {
        console.error('Attempted to add transition but was not in correct state');
        return;
      }

      const validTransitions = getValidBlockToBlockTransitions(context.state);

      // This should never happen... But just in case.
      if (!validTransitions) {
        console.error('Add transition was not in correct state, canceling');
        await context.dispatch(ProjectViewActions.cancelAddingTransition);
        return;
      }

      const transitions = validTransitions.map(t => t.toNode.id === nodeId);

      // Something has gone wrong... There are nodes with the same ID somewhere!
      if (
        transitions.length === 0 ||
        !context.state.selectedResource ||
        !context.state.newTransitionTypeSpecifiedInAddFlow
      ) {
        await context.dispatch(ProjectViewActions.cancelAddingTransition);
        return;
      }

      const newTransition: WorkflowRelationship = {
        node: context.state.selectedResource,
        next: nodeId,
        type: context.state.newTransitionTypeSpecifiedInAddFlow,
        name: context.state.newTransitionTypeSpecifiedInAddFlow,
        expression: '',
        id: uuid()
      };

      await context.dispatch(ProjectViewActions.addTransition, newTransition);
      await context.dispatch(ProjectViewActions.cancelAddingTransition);
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);
      await context.dispatch(ProjectViewActions.selectEdge, newTransition.id);

      // TODO: Open right sidebar pane
    },
    async [ProjectViewActions.openLeftSidebarPane](context, leftSidebarPaneType: SIDEBAR_PANE) {
      if (context.state.isAddingTransitionCurrently) {
        // TODO: Add a shake or something? Tell the user that it's bjorked.
        return;
      }

      // Special case because Mandatory and I agreed that having a pane pop out is annoying af
      if (leftSidebarPaneType === SIDEBAR_PANE.saveProject) {
        await context.dispatch(ProjectViewActions.saveProject);
        return;
      }

      // TODO: Somehow fire a callback on each left pane so that it can reset itself?
      // Using a watcher seems gross... A plugin could work but that feels a little bit too "loose".
      // Better would be a map of Type -> Callback probably? Just trigger other actions to fire?
      // Or have the ProjectEditorLeftPaneContainer fire a callback on the child component?
      // That also feels wrong because it violates to "one direction" principal, in a way.
      context.commit(ProjectViewMutators.setLeftSidebarPane, leftSidebarPaneType);
    },
    [ProjectViewActions.closePane](context, pos: PANE_POSITION) {
      if (pos === PANE_POSITION.left) {
        context.commit(ProjectViewMutators.setLeftSidebarPane, null);
        return;
      }

      if (pos === PANE_POSITION.right) {
        context.commit(ProjectViewMutators.setRightSidebarPane, null);
        return;
      }

      console.error('Attempted to close unknown pane', pos);
    },
    async [ProjectViewActions.openRightSidebarPane](context, paneType: SIDEBAR_PANE) {
      if (context.state.isAddingTransitionCurrently) {
        // TODO: Add a shake or something? Tell the user that it's bjorked.
        return;
      }

      // Special case because Mandatory and I agreed that having a pane pop out is annoying af
      if (paneType === SIDEBAR_PANE.saveProject) {
        await context.dispatch(ProjectViewActions.saveProject);
        return;
      }

      // TODO: Somehow fire a callback on each left pane so that it can reset itself?
      // Using a watcher seems gross... A plugin could work but that feels a little bit too "loose".
      // Better would be a map of Type -> Callback probably? Just trigger other actions to fire?
      // Or have the ProjectEditorLeftPaneContainer fire a callback on the child component?
      // That also feels wrong because it violates to "one direction" principal, in a way.
      context.commit(ProjectViewMutators.setRightSidebarPane, paneType);
    },
    async [ProjectViewActions.resetProjectState](context) {
      context.commit(ProjectViewMutators.selectedResource, null);
      context.commit(ProjectViewMutators.setCytoscapeConfig, null);
      context.commit(ProjectViewMutators.setCytoscapeElements, null);
      context.commit(ProjectViewMutators.setCytoscapeStyle, null);
      context.commit(ProjectViewMutators.setSelectedBlockIndex, null);
      context.commit(ProjectViewMutators.setValidTransitions, null);
      context.commit(ProjectViewMutators.setAddingTransitionStatus, false);

      // TODO: Add "close all panes"
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.right);
    },
    async [ProjectViewActions.addBlock](context, rawBlockType: string) {
      const addBlockWithType = async (addBlockArgs: AddBlockArguments) => await context.dispatch(ProjectViewActions.addIndividualBlock, addBlockArgs);

      await addBlockWithType({
         rawBlockType,
         selectAfterAdding: true
      });

      if (rawBlockType === WorkflowStateType.API_ENDPOINT) {
        await addBlockWithType({
          rawBlockType: WorkflowStateType.API_GATEWAY_RESPONSE,
          selectAfterAdding: false
        });
      }
    },
    // Add Block Pane
    async [ProjectViewActions.addIndividualBlock](context, addBlockArgs: AddBlockArguments) {
      // Call this, for sure
      // await context.dispatch(ProjectViewActions.updateAvailableTransitions)

      // This should not happen
      if (!context.state.openedProject) {
        console.error('Adding block but not project was opened');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      if (addBlockArgs.rawBlockType === 'saved_lambda') {
        await context.dispatch(ProjectViewActions.addSavedBlock);
        return;
      }

      // Catches the case of "unknown" block types causing craziness later!
      if (!Object.values(WorkflowStateType).includes(addBlockArgs.rawBlockType)) {
        console.error('Unknown block type requested to be added!', addBlockArgs.rawBlockType);
        return;
      }

      const blockType = addBlockArgs.rawBlockType as WorkflowStateType;

      // Special casing for the API Response block which should never
      // have it's name changed. Certain blocks will likely make sense for this.
      const immutable_names: WorkflowStateType[] = [
        WorkflowStateType.API_GATEWAY_RESPONSE
      ];

      let newBlockName: string = `Untitled ${blockTypeToImageLookup[blockType].name}`
      if( immutable_names.includes( blockType ) ) {
        newBlockName = blockTypeToImageLookup[blockType].name;
      }

      const newBlock: WorkflowState = {
        ...blockTypeToDefaultStateMapping[blockType],
        id: uuid(),
        // TODO: Make this use a friendly human name
        name: newBlockName,
        type: blockType
      };

      // This creates a new pointer for the main object, which makes Vuex very pleased.
      // TODO: Probably pull this out into a helper function
      const newProject: RefineryProject = {
        ...openedProject,
        workflow_states: [...openedProject.workflow_states, newBlock]
      };

      const params: OpenProjectMutation = {
        project: newProject,
        config: null,
        markAsDirty: true
      };

      await createToast(context.dispatch, {
        title: 'Block Added',
        content: `New block added to project, ${newBlock.name}`,
        variant: ToastVariant.info
      });

      await context.dispatch(ProjectViewActions.updateProject, params);
      if (addBlockArgs.selectAfterAdding) {
        await context.dispatch(ProjectViewActions.selectNode, newBlock.id);
        await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);
      }
    },
    async [ProjectViewActions.addSavedBlock](context) {
      // TODO: Set pane to search
    },
    async [ProjectViewActions.updateExistingBlock](context, node: WorkflowState) {
      // This should not happen
      if (!context.state.openedProject) {
        console.error('Adding block but not project was opened');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      const otherBlocks = openedProject.workflow_states.filter(wfs => wfs.id !== node.id);

      if (otherBlocks.length === openedProject.workflow_states.length) {
        await createToast(context.dispatch, {
          title: 'Invalid Action detected',
          content: 'Updating existing block failed. Block to be updated is not a part of the current project.',
          variant: ToastVariant.danger
        });
        return;
      }

      otherBlocks.push(node);

      // TODO: Probably pull this out into a helper function
      const params: OpenProjectMutation = {
        project: {
          ...openedProject,
          workflow_states: otherBlocks
        },
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },

    // Add Transition Pane
    async [ProjectViewActions.addTransition](context, newTransition: WorkflowRelationship) {
      // This should not happen
      if (!context.state.openedProject) {
        console.error('Adding transition but not project was opened');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      // Validate that the new transition can hit nodes
      const hasValidToNode = openedProject.workflow_states.some(ws => ws.id === newTransition.next);
      const hasValidFromNode = openedProject.workflow_states.some(ws => ws.id === newTransition.node);

      if (!hasValidToNode || !hasValidFromNode) {
        console.error('Tried adding transition to graph with missing nodes!');
        return;
      }

      // This creates a new pointer for the main object, which makes Vuex very pleased.
      const newProject: RefineryProject = {
        ...openedProject,
        workflow_relationships: [...openedProject.workflow_relationships, newTransition]
      };

      const params: OpenProjectMutation = {
        project: newProject,
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
      await context.dispatch(ProjectViewActions.selectEdge, newTransition.id);
    },
    async [ProjectViewActions.updateAvailableTransitions](context) {
      const resetTransitions = () => context.commit(ProjectViewMutators.setValidTransitions, null);

      // This probably should never happen
      if (!context.state.openedProject) {
        // Should we reset the entire state? Feels like it violates the "single responsibility" principle
        // context.dispatch(ProjectViewActions.resetProjectState);

        // Just going to do this as a "safe" measure
        return await resetTransitions();
      }

      const openedProject = context.state.openedProject as RefineryProject;

      if (!context.state.selectedResource) {
        // This feels more reasonable as a sanity check
        return await resetTransitions();
      }

      const selectedResource = context.state.selectedResource as string;

      const selectedNode = getNodeDataById(openedProject, selectedResource);

      // We probably have an Edge selected and this function was called by accident.
      if (!selectedNode) {
        return await resetTransitions();
      }

      // Validation has all passed, so commit the transitions into the state.
      context.commit(ProjectViewMutators.setValidTransitions, selectedNode);
    },
    [ProjectViewActions.cancelAddingTransition](context) {
      context.commit(ProjectViewMutators.setAddingTransitionStatus, false);
      context.commit(ProjectViewMutators.setAddingTransitionType, null);
    },
    async [ProjectViewActions.selectTransitionTypeToAdd](context, transitionType: WorkflowRelationshipType) {
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.right);
      context.commit(ProjectViewMutators.setAddingTransitionStatus, true);
      context.commit(ProjectViewMutators.setAddingTransitionType, transitionType);
    }
  }
};

export default ProjectViewModule;
