/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import uuid from 'uuid/v4';
import {
  IfDropdownSelectionExpressionValues,
  IfDropDownSelectionTypes,
  ProjectViewState,
  RootState
} from '@/store/store-types';
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
import {
  DeploymentViewActions,
  ProjectViewActions,
  ProjectViewGetters,
  ProjectViewMutators
} from '@/constants/store-constants';
import {getApiClient, makeApiRequest} from '@/store/fetchers/refinery-api';
import {API_ENDPOINT} from '@/constants/api-constants';
import {
  DeleteDeploymentsInProjectRequest,
  DeleteDeploymentsInProjectResponse,
  DeployDiagramRequest,
  DeployDiagramResponse,
  GetLatestProjectDeploymentRequest,
  GetLatestProjectDeploymentResponse,
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
  getTransitionDataById,
  getValidBlockToBlockTransitions,
  getValidTransitionsForEdge,
  getValidTransitionsForNode,
  isValidTransition,
  unwrapJson,
  unwrapProjectJson,
  wrapJson
} from '@/utils/project-helpers';
import {
  availableTransitions,
  blockTypeToDefaultStateMapping,
  blockTypeToImageLookup
} from '@/constants/project-editor-constants';
import EditBlockPaneModule, {EditBlockActions} from '@/store/modules/panes/edit-block-pane';
import {createToast} from '@/utils/toasts-utils';
import {ToastVariant} from '@/types/toasts-types';
import router from '@/router';
import {deepJSONCopy} from '@/lib/general-utils';
import EditTransitionPaneModule, {EditTransitionActions} from "@/store/modules/panes/edit-transition-pane";

interface AddBlockArguments {
  rawBlockType: string;
  selectAfterAdding: boolean,
}

export interface ChangeTransitionArguments {
  transition: WorkflowRelationship,
  transitionType: WorkflowRelationshipType
}

const moduleState: ProjectViewState = {
  openedProject: null,
  openedProjectConfig: null,

  openedProjectOriginal: null,
  openedProjectConfigOriginal: null,

  isLoadingProject: true,
  isProjectBusy: false,
  isSavingProject: false,
  isDeployingProject: false,
  hasProjectBeenModified: false,

  leftSidebarPaneState: {
    [SIDEBAR_PANE.runDeployedCodeBlock]: {},
    [SIDEBAR_PANE.runEditorCodeBlock]: {},
    [SIDEBAR_PANE.addBlock]: {},
    [SIDEBAR_PANE.addTransition]: {},
    [SIDEBAR_PANE.allBlocks]: {},
    [SIDEBAR_PANE.allVersions]: {},
    [SIDEBAR_PANE.exportProject]: {},
    [SIDEBAR_PANE.deployProject]: {},
    [SIDEBAR_PANE.saveProject]: {},
    [SIDEBAR_PANE.editBlock]: {},
    [SIDEBAR_PANE.editTransition]: {},
    [SIDEBAR_PANE.viewApiEndpoints]: {},
    [SIDEBAR_PANE.viewExecutions]: {},
    [SIDEBAR_PANE.destroyDeploy]: {},
    [SIDEBAR_PANE.viewDeployedBlock]: {},
    [SIDEBAR_PANE.viewDeployedTransition]: {},
  },
  activeLeftSidebarPane: null,
  activeRightSidebarPane: null,

  // Deployment State
  latestDeploymentState: null,
  deploymentError: null,

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
  availableTransitions: null,
  ifSelectDropdownValue: IfDropDownSelectionTypes.DEFAULT,
  ifExpression: IfDropdownSelectionExpressionValues.DEFAULT,

  // Edit Transition Pane
  availableEditTransitions: null,
  isEditingTransitionCurrently: false,
  newTransitionTypeSpecifiedInEditFlow: null,
};

const ProjectViewModule: Module<ProjectViewState, RootState> = {
  namespaced: true,
  modules: {
    editBlockPane: EditBlockPaneModule,
    editTransitionPanel: EditTransitionPaneModule,
  },
  state: moduleState,
  getters: {
    [ProjectViewGetters.transitionAddButtonEnabled]: state => {
      if (!state.availableTransitions) {
        return false;
      }

      return state.availableTransitions.simple.length > 0 || state.availableTransitions.complex.length > 0;
    },
    /**
     * Used to allow "run code" button to enable only in valid states
     * @param state Vuex state object
     * @return Boolean representing if the button should be enabled
     */
    [ProjectViewGetters.hasCodeBlockSelected]: state => {
      if (!state.selectedResource || !state.openedProject) {
        return false;
      }

      const locatedNode = getNodeDataById(state.openedProject, state.selectedResource);

      if (!locatedNode) {
        return false;
      }

      return locatedNode.type === WorkflowStateType.LAMBDA;
    },
    /**
     * Returns the list of "next" valid blocks to select
     * @param state Vuex state object
     */
    [ProjectViewGetters.getValidBlockToBlockTransitions]: state => getValidBlockToBlockTransitions(state),
    /**
     * Returns which menu items are able to be displayed by the Add Transition pane
     * @param state Vuex state object
     */
    [ProjectViewGetters.getValidMenuDisplayTransitionTypes]: state => {
      if (!state.availableTransitions) {
        // Return an empty list because our state is invalid, but we also hate null types :)
        return [];
      }

      if (state.availableTransitions.complex.length > 0) {
        // Return every type as available
        return availableTransitions;
      }

      if (state.availableTransitions.simple.length > 0) {
        // Only return "then" being enabled
        return [WorkflowRelationshipType.THEN];
      }

      // There are no valid transitions available
      return [];
    },
    /**
     * Returns which menu items are able to be displayed by the Edit Transition pane
     * @param state Vuex state object
     */
    [ProjectViewGetters.getValidEditMenuDisplayTransitionTypes]: state => {
      if (!state.availableEditTransitions) {
        // Return an empty list because our state is invalid, but we also hate null types :)
        return [];
      }

      if (state.availableEditTransitions.complex.length > 0) {
        // Return every type as available
        return availableTransitions;
      }

      if (state.availableEditTransitions.simple.length > 0) {
        // Only return "then" being enabled
        return [WorkflowRelationshipType.THEN];
      }

      // There are no valid transitions available
      return [];
    },
    [ProjectViewGetters.canSaveProject]: state => state.hasProjectBeenModified && !state.isProjectBusy && !state.isAddingTransitionCurrently,
    [ProjectViewGetters.canDeployProject]: state =>
      !state.hasProjectBeenModified && !state.isProjectBusy && !state.isAddingTransitionCurrently && !state.isEditingTransitionCurrently
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
    [ProjectViewMutators.isSavingProject](state, value: boolean) {
      state.isSavingProject = value;
    },
    [ProjectViewMutators.isDeployingProject](state, value: boolean) {
      state.isDeployingProject = value;
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

    // Deployment Logic
    [ProjectViewMutators.setLatestDeploymentState](state, response: GetLatestProjectDeploymentResponse | null) {
      state.latestDeploymentState = response;
    },
    [ProjectViewMutators.setDeploymentError](state, error: string | null) {
      state.deploymentError = error;
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

    [ProjectViewMutators.setIfDropdownSelection](state, dropdownSelection: IfDropDownSelectionTypes) {
      state.ifSelectDropdownValue = dropdownSelection;
    },
    [ProjectViewMutators.setIfExpression](state, ifExpression: string) {
      state.ifExpression = ifExpression;
    },
    [ProjectViewMutators.setValidTransitions](state, node: WorkflowState) {
      if (!node || !state.openedProject) {
        state.availableTransitions = null;
        return;
      }

      // Assigning this in a mutator because this algorithm is O(n^2) and that feels bad in a getter
      state.availableTransitions = getValidTransitionsForNode(state.openedProject, node);
    },

    // Edit Transition Pane
    [ProjectViewMutators.setValidEditTransitions](state, edge: WorkflowRelationship) {
      if (!edge || !state.openedProject) {
        state.availableEditTransitions = null;
        return;
      }

      // Assigning this in a mutator because this algorithm is O(n^2) and that feels bad in a getter
      state.availableEditTransitions = getValidTransitionsForEdge(state.openedProject, edge);
    },
    [ProjectViewMutators.setEditingTransitionStatus](state, editingCurrently: boolean) {
      state.isEditingTransitionCurrently = editingCurrently;
    },
    [ProjectViewMutators.setEditingTransitionType](state, transitionType: WorkflowRelationshipType | null) {
      state.newTransitionTypeSpecifiedInEditFlow = transitionType;
    },
  },
  actions: {
    async [ProjectViewActions.setIfExpression](context, ifExpressionValue: string) {
      await context.commit(ProjectViewMutators.setIfExpression, ifExpressionValue);
    },
    async [ProjectViewActions.ifDropdownSelection](context, dropdownSelection: IfDropDownSelectionTypes | null) {
      if (dropdownSelection === null) {
        await context.commit(ProjectViewMutators.setIfExpression, IfDropdownSelectionExpressionValues.DEFAULT);
        await context.commit(ProjectViewMutators.setIfDropdownSelection, dropdownSelection);
        return;
      }
      const ifExpressionValue: string = IfDropdownSelectionExpressionValues[dropdownSelection];
      await context.commit(ProjectViewMutators.setIfExpression, ifExpressionValue);
      await context.commit(ProjectViewMutators.setIfDropdownSelection, dropdownSelection);
    },
    async [ProjectViewActions.deselectResources](context) {
      await context.commit(ProjectViewMutators.selectedResource, null);
    },
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
      const handleSaveError = async (message: string) => {
        context.commit(ProjectViewMutators.isSavingProject, false);
        console.error(message);
        await createToast(context.dispatch, {
          title: 'Save Error',
          content: message,
          variant: ToastVariant.danger
        });
      };
      if (!context.state.openedProject || !context.state.openedProjectConfig || !context.state.hasProjectBeenModified) {
        await handleSaveError('Project attempted to be saved but it was not in a valid state');
        return;
      }

      context.commit(ProjectViewMutators.isSavingProject, true);

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
        await handleSaveError('Unable to save project: server failure.');
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

      await context.dispatch(ProjectViewActions.updateProject, params);

      context.commit(ProjectViewMutators.isSavingProject, false);
    },
    async [ProjectViewActions.fetchLatestDeploymentState](context) {
      if (!context.state.openedProject) {
        console.error('Tried to fetch project deploy status without opened project');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      const latestDeploymentResponse = await makeApiRequest<GetLatestProjectDeploymentRequest, GetLatestProjectDeploymentResponse>(
        API_ENDPOINT.GetLatestProjectDeployment,
        {
          project_id: openedProject.project_id
        }
      );

      context.commit(ProjectViewMutators.setLatestDeploymentState, latestDeploymentResponse);
    },
    async [ProjectViewActions.deployProject](context) {
      const handleDeploymentError = async (message: string) => {
        context.commit(ProjectViewMutators.isDeployingProject, false);
        console.error(message);
        await createToast(context.dispatch, {
          title: 'Deployment Error',
          content: message,
          variant: ToastVariant.danger
        });
      };

      if (!context.state.openedProject || !context.state.openedProjectConfig || !context.getters[ProjectViewGetters.canDeployProject]) {
        console.error('Tried to deploy project but should not have been enabled');
        return;
      }

      context.commit(ProjectViewMutators.setDeploymentError, null);
      context.commit(ProjectViewMutators.isDeployingProject, true);

      const openedProject = context.state.openedProject as RefineryProject;

      if (!context.state.latestDeploymentState) {
        return await handleDeploymentError('Missing latest project deployment information');
      }

      if (context.state.latestDeploymentState.result && context.state.latestDeploymentState.result.deployment_json) {
        const deleteDeploymentResponse = await makeApiRequest<DeleteDeploymentsInProjectRequest, DeleteDeploymentsInProjectResponse>(
          API_ENDPOINT.DeleteDeploymentsInProject,
          {
            project_id: openedProject.project_id
          }
        );

        if (!deleteDeploymentResponse) {
          return await handleDeploymentError('Unable to delete existing deployment.');
        }
      }

      const projectJson = wrapJson(openedProject);

      if (!projectJson) {
        return await handleDeploymentError('Unable to send project to server.');
      }

      const createDeploymentResponse = await makeApiRequest<DeployDiagramRequest, DeployDiagramResponse>(
        API_ENDPOINT.DeployDiagram,
        {
          diagram_data: projectJson,
          project_config: context.state.openedProjectConfig,
          project_id: context.state.openedProject.project_id,
          project_name: context.state.openedProject.name
        }
      );

      if (!createDeploymentResponse) {
        return await handleDeploymentError('Unable to create new deployment.');
      }

      context.commit(ProjectViewMutators.isDeployingProject, false);
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);

      router.push({
        name: 'deployment',
        params: {
          projectId: openedProject.project_id
        }
      });
    },
    async [ProjectViewActions.showDeploymentPane](context) {
      if (!context.state.openedProject || !context.getters[ProjectViewGetters.canDeployProject]) {
        console.error('Tried to show deployment pane with missing state');
        context.commit(ProjectViewMutators.setDeploymentError, 'Error: Invalid state for Deployment');
        return;
      }

      context.commit(ProjectViewMutators.setDeploymentError, null);

      await context.dispatch(ProjectViewActions.fetchLatestDeploymentState);

      if (!context.state.latestDeploymentState) {
        context.commit(ProjectViewMutators.isDeployingProject, false);
        const message = 'Unable to retrieve latest project deployment information';
        console.error(message);
        await createToast(context.dispatch, {
          title: 'Deployment Error',
          content: message,
          variant: ToastVariant.danger
        });
        return;
      }
    },
    async [ProjectViewActions.resetDeploymentPane](context) {
      context.commit(ProjectViewMutators.setLatestDeploymentState, null);
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);
      context.commit(ProjectViewMutators.setDeploymentError, null);
    },

    async [ProjectViewActions.clearSelection](context) {
      if (context.state.isAddingTransitionCurrently) {
        return;
      }

      if (context.state.isEditingTransitionCurrently) {
        return;
      }

      context.commit(ProjectViewMutators.selectedResource, null);
      await context.dispatch(ProjectViewActions.updateAvailableTransitions)
      await context.dispatch(ProjectViewActions.updateAvailableEditTransitions);
    },
    async [ProjectViewActions.selectNode](context, nodeId: string) {
      if (context.state.isAddingTransitionCurrently) {
        await context.dispatch(ProjectViewActions.completeTransitionAdd, nodeId);
        return;
      }

      await context.dispatch(ProjectViewActions.resetPanelStates);

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

      const node = deepJSONCopy(nodes[0]);

      context.commit(ProjectViewMutators.selectedResource, node.id);

      await context.dispatch(ProjectViewActions.updateAvailableTransitions);

      // Opens up the Edit block pane
      await context.dispatch(ProjectViewActions.openRightSidebarPane, SIDEBAR_PANE.editBlock);
      await context.dispatch(`editBlockPane/${EditBlockActions.selectCurrentlySelectedProjectNode}`);
    },
    async [ProjectViewActions.selectEdge](context, edgeId: string) {
      // I don't have a good answer for this, but my best guess is that
      // just having a reset pane state call for edge and node selection is
      // the best way to go about this? This may cause users to lose their
      // current state though :( so maybe detect it and stop it?
      await context.dispatch(ProjectViewActions.resetPanelStates);

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

      const selectedEdge = edges[0];

      context.commit(ProjectViewMutators.selectedResource, selectedEdge.id);

      // If we're editing an "IF" transition, skip directly to the secondary transition panel
      if(selectedEdge.type === WorkflowRelationshipType.IF) {
        await context.dispatch(ProjectViewActions.selectTransitionTypeToEdit, WorkflowRelationshipType.IF);
      }

      await context.dispatch(DeploymentViewActions.openRightSidebarPane, SIDEBAR_PANE.editTransition);
      await context.dispatch(ProjectViewActions.updateAvailableEditTransitions);
      await context.dispatch(`editTransitionPanel/${EditTransitionActions.selectCurrentlySelectedProjectEdge}`);
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
        expression: context.state.ifExpression,
        id: uuid()
      };

      if (context.state.openedProject === null) {
        console.error("Something odd has occurred, you're trying to add a transition with no project opened!");
        await context.dispatch(ProjectViewActions.cancelAddingTransition);
        return;
      }

      // Ensure we have a valid transition
      const toNode = getNodeDataById(context.state.openedProject, nodeId);
      const fromNode = getNodeDataById(context.state.openedProject, context.state.selectedResource);

      if (toNode === null || fromNode === null) {
        console.error("Something odd has occurred, you have an unknown node selected for this transition!");
        await context.dispatch(ProjectViewActions.cancelAddingTransition);
        return;
      }

      // Validate the transition is possible. e.g. Not Code Block -> Timer Block
      if (!isValidTransition(fromNode, toNode)) {
        await createToast(context.dispatch, {
          title: 'Error, invalid transition!',
          content: "That is not a valid transition, please select one of the flashing blocks to add a valid transition.",
          variant: ToastVariant.danger
        });
        return;
      }

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
        // Close any existing panes... Because it's ridiculous otherwise.
        context.commit(ProjectViewMutators.setLeftSidebarPane, null);
        await context.dispatch(ProjectViewActions.saveProject);
        return;
      }

      // TODO: Somehow fire a callback on each left pane so that it can reset itself?
      // Using a watcher seems gross... A plugin could work but that feels a little bit too "loose".
      // Better would be a map of Type -> Callback probably? Just trigger other actions to fire?
      // Or have the ProjectEditorLeftPaneContainer fire a callback on the child component?
      // That also feels wrong because it violates to "one direction" principal, in a way.
      context.commit(ProjectViewMutators.setLeftSidebarPane, leftSidebarPaneType);

      if (leftSidebarPaneType === SIDEBAR_PANE.deployProject) {
        // TODO: Is this better inside of a `mounted` hook?
        await context.dispatch(ProjectViewActions.showDeploymentPane);
        return;
      }
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
    async [ProjectViewActions.resetPanelStates](context) {
      context.commit(ProjectViewMutators.selectedResource, null);
      context.commit(ProjectViewMutators.setSelectedBlockIndex, null);

      context.commit(ProjectViewMutators.setValidTransitions, null);
      context.commit(ProjectViewMutators.setValidEditTransitions, null);

      await context.dispatch(ProjectViewActions.cancelAddingTransition);
      await context.dispatch(ProjectViewActions.cancelEditingTransition);

      // TODO: Add "close all panes"
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.right);
    },
    async [ProjectViewActions.resetProjectState](context) {
      // All state relating to panels/editing
      await context.dispatch(ProjectViewActions.resetPanelStates);

      // Cytoscape
      context.commit(ProjectViewMutators.setCytoscapeConfig, null);
      context.commit(ProjectViewMutators.setCytoscapeElements, null);
      context.commit(ProjectViewMutators.setCytoscapeStyle, null);

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
      if (immutable_names.includes(blockType)) {
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
    async [ProjectViewActions.changeExistingTransition](context, ChangeTransitionArgumentsValue: ChangeTransitionArguments) {
      // This should not happen
      if (!context.state.openedProject) {
        console.error('Tried to delete a transition but no project was open!');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      const modifiedTransitions = openedProject.workflow_relationships.map(wfr => {
        // Careful there boy
        const workflowRelationship = deepJSONCopy(wfr);
        if (ChangeTransitionArgumentsValue.transition.id === workflowRelationship.id) {
          workflowRelationship.name = ChangeTransitionArgumentsValue.transitionType;
          workflowRelationship.type = ChangeTransitionArgumentsValue.transitionType;

          if (workflowRelationship.type === WorkflowRelationshipType.IF) {
            workflowRelationship.expression = context.state.ifExpression;
          } else {
            workflowRelationship.expression = "";
          }
        }
        return workflowRelationship;
      });

      // TODO: Probably pull this out into a helper function
      const params: OpenProjectMutation = {
        project: {
          ...openedProject,
          workflow_relationships: modifiedTransitions
        },
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },
    async [ProjectViewActions.deleteExistingTransition](context, transition: WorkflowRelationship) {
      // This should not happen
      if (!context.state.openedProject) {
        console.error('Tried to delete a transition but no project was open!');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      const otherTransitions = deepJSONCopy(openedProject.workflow_relationships.filter(wfs => wfs.id !== transition.id));

      // TODO: Probably pull this out into a helper function
      const params: OpenProjectMutation = {
        project: {
          ...openedProject,
          workflow_relationships: otherTransitions
        },
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },
    async [ProjectViewActions.deleteExistingBlock](context, node: WorkflowState) {
      // This should not happen
      if (!context.state.openedProject) {
        console.error('Adding block but no project was open!');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      const otherBlocks = deepJSONCopy(openedProject.workflow_states.filter(wfs => wfs.id !== node.id));

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

      const otherBlocks = deepJSONCopy(openedProject.workflow_states.filter(wfs => wfs.id !== node.id));

      if (otherBlocks.length === openedProject.workflow_states.length) {
        await createToast(context.dispatch, {
          title: 'Invalid Action detected',
          content: 'Updating existing block failed. Block to be updated is not a part of the current project.',
          variant: ToastVariant.danger
        });
        return;
      }

      otherBlocks.push(deepJSONCopy(node));

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
    async [ProjectViewActions.updateAvailableEditTransitions](context) {
      const resetTransitions = () => context.commit(ProjectViewMutators.setValidEditTransitions, null);

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

      const selectedEdge = getTransitionDataById(openedProject, selectedResource);

      // We probably have an Edge selected and this function was called by accident.
      if (!selectedEdge) {
        return await resetTransitions();
      }

      // Validation has all passed, so commit the transitions into the state.
      context.commit(ProjectViewMutators.setValidEditTransitions, selectedEdge);
    },
    async [ProjectViewActions.cancelAddingTransition](context) {
      await context.dispatch(ProjectViewActions.ifDropdownSelection, IfDropDownSelectionTypes.DEFAULT);
      await context.dispatch(ProjectViewActions.setIfExpression, IfDropdownSelectionExpressionValues.DEFAULT);
      context.commit(ProjectViewMutators.setAddingTransitionStatus, false);
      context.commit(ProjectViewMutators.setAddingTransitionType, null);
    },
    async [ProjectViewActions.cancelEditingTransition](context) {
      await context.dispatch(ProjectViewActions.ifDropdownSelection, IfDropDownSelectionTypes.DEFAULT);
      await context.dispatch(ProjectViewActions.setIfExpression, IfDropdownSelectionExpressionValues.DEFAULT);
      context.commit(ProjectViewMutators.setEditingTransitionStatus, false);
      context.commit(ProjectViewMutators.setEditingTransitionType, null);
    },
    async [ProjectViewActions.selectTransitionTypeToEdit](context, transitionType: WorkflowRelationshipType) {
      if (context.state.selectedResource === null) {
        console.error("For some reason the selected resource is null, that shouldn't happen!");
        return;
      }

      // If we're editing we only open the secondary panel when the "IF" transition is selected
      if (transitionType === WorkflowRelationshipType.IF) {
        const selectedResource = context.state.selectedResource as string;
        const openedProject = context.state.openedProject as RefineryProject;

        const selectedEdge = getTransitionDataById(openedProject, selectedResource);

        if (selectedEdge === null) {
          console.error("You've somehow selected an edge that no longer exists, how'd you do that?");
          return;
        }

        // Set the ifExpression to reflect the selected transition
        if (selectedEdge.expression !== "") {
          await context.dispatch(ProjectViewActions.setIfExpression, selectedEdge.expression);
        }

        await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);
        context.commit(ProjectViewMutators.setEditingTransitionStatus, true);
        context.commit(ProjectViewMutators.setEditingTransitionType, transitionType);
        return;
      }
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.right);

      // Change the transition to the new type
      await context.dispatch(`editTransitionPanel/${EditTransitionActions.changeTransitionType}`, transitionType);
      await context.dispatch(ProjectViewActions.cancelEditingTransition);
    },
    async [ProjectViewActions.selectTransitionTypeToAdd](context, transitionType: WorkflowRelationshipType) {
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.right);
      context.commit(ProjectViewMutators.setAddingTransitionStatus, true);
      context.commit(ProjectViewMutators.setAddingTransitionType, transitionType);
    },
  }
};

export default ProjectViewModule;