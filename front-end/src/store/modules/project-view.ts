import { Module } from 'vuex';
import uuid from 'uuid/v4';
import LZString from 'lz-string';
import {
  IfDropdownSelectionExpressionValues,
  IfDropDownSelectionType,
  ProjectViewState,
  RootState
} from '@/store/store-types';
import {
  ProjectConfig,
  ProjectLogLevel,
  RefineryProject,
  SupportedLanguage,
  WorkflowFile,
  WorkflowFileLink,
  WorkflowFileLinkType,
  WorkflowFileType,
  WorkflowRelationship,
  WorkflowRelationshipType,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { generateCytoscapeElements, generateCytoscapeStyle } from '@/lib/refinery-to-cytoscript-converter';
import { CssStyleDeclaration, LayoutOptions } from 'cytoscape';
import cytoscape from '@/components/CytoscapeGraph';
import {
  DeploymentViewActions,
  ProjectViewActions,
  ProjectViewGetters,
  ProjectViewMutators,
  UserActions
} from '@/constants/store-constants';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import {
  GetLatestProjectDeploymentRequest,
  GetLatestProjectDeploymentResponse,
  GetProjectConfigRequest,
  GetProjectConfigResponse,
  GetSavedProjectRequest,
  ImportProjectRepoRequest,
  ImportProjectRepoResponse,
  SaveProjectConfigRequest,
  SaveProjectConfigResponse,
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
  getIDsOfBlockType,
  getNodeDataById,
  getTransitionDataById,
  getValidBlockToBlockTransitions,
  getValidTransitionsForEdge,
  getValidTransitionsForNode,
  isValidTransition,
  unwrapJson,
  wrapJson
} from '@/utils/project-helpers';
import { availableTransitions, DEFAULT_LANGUAGE_CODE, savedBlockType } from '@/constants/project-editor-constants';
import { blockTypeToImageLookup } from '@/constants/project-editor-img-constants';
import { demoModeBlacklist } from '@/constants/project-editor-pane-constants';
import EditBlockPaneModule, { EditBlockActions, EditBlockGetters } from '@/store/modules/panes/edit-block-pane';
import { createToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';
import router from '@/router';
import { deepJSONCopy } from '@/lib/general-utils';
import EditTransitionPaneModule, { EditTransitionActions } from '@/store/modules/panes/edit-transition-pane';
import {
  createShortlink,
  deployProject,
  importProjectRepo,
  openProject,
  teardownProject
} from '@/store/fetchers/api-helpers';
import { CyElements, CyStyle } from '@/types/cytoscape-types';
import { addAPIBlocksToProject, createNewBlock, createNewTransition } from '@/utils/block-utils';
import { saveEditBlockToProject } from '@/utils/store-utils';
import ImportableRefineryProject from '@/types/export-project';
import { AllProjectsActions, AllProjectsGetters } from '@/store/modules/all-projects';
import { kickOffLibraryBuildForBlocks } from '@/utils/block-build-utils';
import { AddSharedFileArguments, AddSharedFileLinkArguments } from '@/types/shared-files';
import { EditSharedFilePaneModule } from '@/store';
import { compileProjectRepo } from '@/repo-compiler/lift';
import { saveProjectToRepo } from '@/repo-compiler/drop';
import generateStupidName from '@/lib/silly-names';
import slugify from 'slugify';

export interface ChangeTransitionArguments {
  transition: WorkflowRelationship;
  transitionType: WorkflowRelationshipType;
}

export interface AddBlockArguments {
  rawBlockType: string;
  selectAfterAdding: boolean;
  /**
   * This block is "extended" from during the add flow, if specified. Example use case: Adding a saved block.
   */
  customBlockProperties?: WorkflowState;
}

const moduleState: ProjectViewState = {
  openedProject: null,
  openedProjectConfig: null,

  openedProjectOriginal: null,
  openedProjectConfigOriginal: null,

  isInDemoMode: false,
  isCreatingShortlink: false,
  shortlinkUrl: null,

  isLoadingProject: false,
  isProjectBusy: false,
  isSavingProject: false,
  isDeployingProject: false,
  hasProjectBeenModified: false,

  leftSidebarPaneState: {
    [SIDEBAR_PANE.runDeployedCodeBlock]: {},
    [SIDEBAR_PANE.runEditorCodeBlock]: {},
    [SIDEBAR_PANE.addBlock]: {},
    [SIDEBAR_PANE.addSavedBlock]: {},
    [SIDEBAR_PANE.addTransition]: {},
    [SIDEBAR_PANE.allBlocks]: {},
    [SIDEBAR_PANE.allVersions]: {},
    [SIDEBAR_PANE.exportProject]: {},
    [SIDEBAR_PANE.deployProject]: {},
    [SIDEBAR_PANE.saveProject]: {},
    [SIDEBAR_PANE.importProjectRepo]: {},
    [SIDEBAR_PANE.editBlock]: {},
    [SIDEBAR_PANE.editTransition]: {},
    [SIDEBAR_PANE.viewApiEndpoints]: {},
    [SIDEBAR_PANE.viewExecutions]: {},
    [SIDEBAR_PANE.destroyDeploy]: {},
    [SIDEBAR_PANE.viewDeployedBlock]: {},
    [SIDEBAR_PANE.viewDeployedBlockLogs]: {},
    [SIDEBAR_PANE.viewDeployedTransition]: {},
    [SIDEBAR_PANE.sharedFiles]: {},
    [SIDEBAR_PANE.editSharedFile]: {},
    [SIDEBAR_PANE.editSharedFileLinks]: {},
    [SIDEBAR_PANE.addingSharedFileLink]: {},
    [SIDEBAR_PANE.codeBlockSharedFiles]: {},
    [SIDEBAR_PANE.viewSharedFile]: {},
    [SIDEBAR_PANE.viewReadme]: {},
    [SIDEBAR_PANE.editReadme]: {}
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
  ifSelectDropdownValue: IfDropDownSelectionType.DEFAULT,
  ifExpression: '',

  // Edit Transition Pane
  availableEditTransitions: null,
  isEditingTransitionCurrently: false,
  newTransitionTypeSpecifiedInEditFlow: null,

  // Adding a shared block to a file
  isAddingSharedFileToCodeBlock: false
};

const ProjectViewModule: Module<ProjectViewState, RootState> = {
  namespaced: true,
  modules: {
    editBlockPane: EditBlockPaneModule,
    editTransitionPane: EditTransitionPaneModule
  },
  state: deepJSONCopy(moduleState),
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
     * Returns the list of IDs for all of the valid Code Blocks in the project.
     *
     * This is a getter for the animation for the Add Shared File to Code Block functionality.
     */
    [ProjectViewGetters.getCodeBlockIDs]: state => {
      if (state.openedProject === null) {
        return [];
      }

      // TODO: Return only valid blocks here, not all Lambda blocks.
      return getIDsOfBlockType(WorkflowStateType.LAMBDA, state.openedProject);
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
    [ProjectViewGetters.canSaveProject]: (state, getters, rootState, rootGetters) => {
      const editedBlockIsValid = rootGetters[`project/editBlockPane/${EditBlockGetters.isEditedBlockValid}`];

      const isEditorStateValid = !state.isProjectBusy && !state.isAddingTransitionCurrently && editedBlockIsValid;

      if (!isEditorStateValid) {
        return false;
      }

      // If the block is dirty, we will save it + then save the project.
      if (rootGetters[`project/editBlockPane/${EditBlockGetters.isStateDirty}`]) {
        return true;
      }

      // If the block is dirty, we will save it + then save the project.
      if (getters[ProjectViewGetters.selectedTransitionDirty]) {
        return true;
      }

      return state.hasProjectBeenModified;
    },
    [ProjectViewGetters.canDeployProject]: state => !state.isProjectBusy && !state.isAddingTransitionCurrently,
    [ProjectViewGetters.selectedBlockDirty]: (state, getters) =>
      state.editBlockPane && getters['editBlockPane/isStateDirty'],
    [ProjectViewGetters.selectedTransitionDirty]: (state, getters) =>
      state.editTransitionPane && getters['editTransitionPane/isStateDirty'],
    [ProjectViewGetters.selectedResourceDirty]: (state, getters) =>
      getters[ProjectViewGetters.selectedBlockDirty] || getters[ProjectViewGetters.selectedTransitionDirty],
    [ProjectViewGetters.exportProjectJson]: state => {
      if (!state.openedProject) {
        return '';
      }

      // We ignore project_id because we just don't want it in the JSON
      const { project_id, ...rest } = state.openedProject;

      return JSON.stringify(rest, null, '  ');
    },
    [ProjectViewGetters.shareProjectUrl]: state => {
      if (!state.openedProject) {
        return '';
      }

      if (state.isCreatingShortlink) {
        return '';
      }

      if (state.shortlinkUrl) {
        return `https://app.refinery.io/import?q=${state.shortlinkUrl}`;
      }

      // We ignore project_id because we just don't want it in the JSON
      const { project_id, version, ...rest } = state.openedProject;

      const compressedData = LZString.compressToEncodedURIComponent(JSON.stringify(rest));

      return `https://app.refinery.io/import#${compressedData}`;
    },
    [ProjectViewGetters.isProjectRepoSet]: state => {
      return state.openedProjectConfig && state.openedProjectConfig.project_repo;
    }
  },
  mutations: {
    [ProjectViewMutators.resetState](state) {
      // TODO: Turn this into a helper function.
      Object.keys(moduleState).forEach(key => {
        // @ts-ignore
        state[key] = deepJSONCopy(moduleState[key]);
      });
    },
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
    [ProjectViewMutators.setDemoMode](state, value: boolean) {
      state.isInDemoMode = value;
    },
    [ProjectViewMutators.setIsCreatingShortlink](state, value: boolean) {
      state.isCreatingShortlink = value;
    },
    [ProjectViewMutators.setShortlinkUrl](state, value: string | null) {
      state.shortlinkUrl = value;
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
      state.cytoscapeElements = deepJSONCopy(elements);
    },
    [ProjectViewMutators.setCytoscapeStyle](state, stylesheet: CyStyle) {
      state.cytoscapeStyle = deepJSONCopy(stylesheet);
    },
    [ProjectViewMutators.setCytoscapeLayout](state, layout: LayoutOptions) {
      state.cytoscapeLayoutOptions = deepJSONCopy(layout);
    },
    [ProjectViewMutators.setCytoscapeConfig](state, config: cytoscape.CytoscapeOptions) {
      state.cytoscapeConfig = deepJSONCopy(config);
    },
    [ProjectViewMutators.setIsAddingSharedFileToCodeBlock](state, value: boolean) {
      state.isAddingSharedFileToCodeBlock = value;
    },
    // Project Config
    [ProjectViewMutators.setProjectLogLevel](state, projectLoggingLevel: ProjectLogLevel) {
      if (state.openedProjectConfig === null) {
        console.error('Could not set project log level due to no project being opened.');
        return;
      }
      state.openedProjectConfig = Object.assign({}, state.openedProjectConfig, {
        logging: {
          ...state.openedProjectConfig.logging,
          level: projectLoggingLevel
        }
      });
    },
    [ProjectViewMutators.setProjectRuntimeLanguage](state, projectRuntimeLanguage: SupportedLanguage) {
      if (state.openedProjectConfig === null) {
        console.error('Could not set project runtime language due to no project being opened.');
        return;
      }
      state.openedProjectConfig = {
        ...state.openedProjectConfig,
        default_language: projectRuntimeLanguage
      };
    },
    [ProjectViewMutators.setProjectRepo](state, projectRepo: string) {
      if (state.openedProjectConfig === null) {
        console.error('Could not set project git repo due to no project being opened.');
        return;
      }
      state.openedProjectConfig = {
        ...state.openedProjectConfig,
        project_repo: projectRepo
      };
    },

    // Deployment Logic
    [ProjectViewMutators.setLatestDeploymentState](state, response: GetLatestProjectDeploymentResponse | null) {
      state.latestDeploymentState = response;
    },
    [ProjectViewMutators.setDeploymentError](state, error) {
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

    [ProjectViewMutators.setIfDropdownSelection](state, dropdownSelection: IfDropDownSelectionType) {
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
    }
  },
  actions: {
    async [ProjectViewActions.setWarmupConcurrencyLevel](context, warmupConcurrencyLevel: number) {
      if (context.state.openedProjectConfig === null) {
        console.error("Can't set warmup concurrency level because no project is opened!");
        return;
      }

      const newProjectConfig = Object.assign({}, context.state.openedProjectConfig, {
        warmup_concurrency_level: warmupConcurrencyLevel
      });

      const params: OpenProjectMutation = {
        project: null,
        config: newProjectConfig,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },
    async [ProjectViewActions.setProjectConfigLoggingLevel](context, projectLoggingLevel: ProjectLogLevel) {
      context.commit(ProjectViewMutators.setProjectLogLevel, projectLoggingLevel);

      // Save new config to the backend
      await context.dispatch(ProjectViewActions.saveProjectConfig);
    },
    async [ProjectViewActions.setProjectConfigRuntimeLanguage](
      context,
      projectConfigRuntimeLanguage: SupportedLanguage
    ) {
      context.commit(ProjectViewMutators.setProjectRuntimeLanguage, projectConfigRuntimeLanguage);

      // Save new config to the backend
      await context.dispatch(ProjectViewActions.saveProjectConfig);
    },
    async [ProjectViewActions.setProjectConfigRepo](context, projectConfigRepo: string) {
      context.commit(ProjectViewMutators.setProjectRepo, projectConfigRepo);

      // Save new config to the backend
      await context.dispatch(ProjectViewActions.saveProjectConfig);
    },
    async [ProjectViewActions.setIfExpression](context, ifExpressionValue: string) {
      await context.commit(ProjectViewMutators.setIfExpression, ifExpressionValue);
    },
    async [ProjectViewActions.ifDropdownSelection](context, dropdownSelection: IfDropDownSelectionType | null) {
      if (dropdownSelection === null) {
        await context.commit(ProjectViewMutators.setIfExpression, '');
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
      if (!request) {
        // TODO: Handle error gracefully
        console.error('Unable to open project, missing request');
        context.commit(ProjectViewMutators.isLoadingProject, false);
        return;
      }

      context.commit(ProjectViewMutators.resetState);
      context.commit(ProjectViewMutators.isLoadingProject, true);
      await context.dispatch(`deployment/${DeploymentViewActions.resetDeploymentState}`, null, { root: true });

      const project = await openProject(request);

      if (!project) {
        // TODO: Handle error gracefully
        console.error('Unable to open project missing project');
        context.commit(ProjectViewMutators.isLoadingProject, false);
        return;
      }

      const params: OpenProjectMutation = {
        project: project,
        config: null,
        markAsDirty: false
      };

      await context.dispatch(ProjectViewActions.updateProject, params);

      await context.dispatch(ProjectViewActions.loadProjectConfig);

      context.commit(ProjectViewMutators.isLoadingProject, false);

      kickOffLibraryBuildForBlocks(project.workflow_states);
    },
    async [ProjectViewActions.openDemo](context) {
      context.commit(ProjectViewMutators.isLoadingProject, true);

      await context.dispatch(`allProjects/${AllProjectsActions.openProjectShareLink}`, null, { root: true });

      context.commit(ProjectViewMutators.isLoadingProject, false);

      const demoProject: ImportableRefineryProject =
        context.rootGetters[`allProjects/${AllProjectsGetters.importProjectFromUrlJson}`];

      if (!demoProject) {
        console.error('Unable to open demo, missing project');
        return;
      }

      context.commit(ProjectViewMutators.resetState);
      context.commit(ProjectViewMutators.setDemoMode, true);

      const params: OpenProjectMutation = {
        project: {
          // Default values in the event these are not specified in the imported JSON
          workflow_files: [],
          workflow_file_links: [],
          readme: ``,
          // Merge in the JSON object and setup other properties with new values
          ...demoProject,
          project_id: uuid(),
          version: 1
        },
        config: {
          environment_variables: {},
          warmup_concurrency_level: 0,
          api_gateway: { gateway_id: false },
          logging: { level: ProjectLogLevel.LOG_ALL },
          default_language: SupportedLanguage.NODEJS_8,
          project_repo: '',
          version: '1'
        },
        // We mark it as dirty so that we always show the save button ;)
        markAsDirty: false
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },
    async [ProjectViewActions.updateProject](context, params: OpenProjectMutation) {
      const stylesheetOverrides: CssStyleDeclaration = Object.keys(
        context.rootState.blockLocalCodeSync.blockIdToJobIdLookup
      ).map(blockId => {
        return {
          selector: `#${blockId}`,
          style: { 'background-image': require('../../../public/img/node-icons/code-icon-local-sync.png') }
        };
      });

      const stylesheet = generateCytoscapeStyle(stylesheetOverrides);

      if (params.config) {
        context.commit(ProjectViewMutators.setOpenedProjectConfig, params.config);
      }

      const cleanProject = !params.markAsDirty;

      if (cleanProject && params.project) {
        context.commit(ProjectViewMutators.setOpenedProjectOriginal, params.project);
      }

      if (cleanProject && params.config) {
        context.commit(ProjectViewMutators.setOpenedProjectConfig, params.config);
      }

      // TODO: Make this actually compare IDs or something... But maybe we can hack it with Undo?
      context.commit(ProjectViewMutators.markProjectDirtyStatus, params.markAsDirty);

      if (params.project) {
        const elements = generateCytoscapeElements(params.project);
        context.commit(ProjectViewMutators.setOpenedProject, params.project);
        context.commit(ProjectViewMutators.setCytoscapeElements, elements);
      }

      context.commit(ProjectViewMutators.setCytoscapeStyle, stylesheet);
    },
    async [ProjectViewActions.saveProjectConfig](context) {
      const handleSaveError = async (message: string) => {
        context.commit(ProjectViewMutators.isSavingProject, false);
        console.error(message);
        await createToast(context.dispatch, {
          title: 'Save Config Error',
          content: message,
          variant: ToastVariant.danger
        });
      };

      if (!context.state.openedProject || !context.state.openedProjectConfig) {
        await handleSaveError('Project attempted to be saved but it was not in a valid state');
        return;
      }

      context.commit(ProjectViewMutators.isSavingProject, true);

      const configJson = wrapJson(context.state.openedProjectConfig);

      if (!configJson) {
        console.error('Unable to serialize project config into JSON data');
        return;
      }

      const response = await makeApiRequest<SaveProjectConfigRequest, SaveProjectConfigResponse>(
        API_ENDPOINT.SaveProjectConfig,
        {
          project_id: context.state.openedProject.project_id,
          config: configJson
        }
      );
      if (response === null || !response.success) {
        await handleSaveError('Unable to save project config: server failure.');
        return;
      }

      context.commit(ProjectViewMutators.isSavingProject, false);

      await createToast(context.dispatch, {
        title: 'Project Config Updated',
        content: 'Project settings saved successfully!',
        variant: ToastVariant.success
      });
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

      // Check that the "canSaveProject" getter is passing, that way we centralize our logic in one place.
      if (
        !context.getters[ProjectViewGetters.canSaveProject] ||
        !context.state.openedProject ||
        !context.state.openedProjectConfig
      ) {
        await handleSaveError('Project attempted to be saved but it was not in a valid state');
        return;
      }

      // Project repo is set, drop to fs and push to git
      if (context.state.openedProjectConfig.project_repo) {
        await context.dispatch(ProjectViewActions.saveToProjectRepo, null);
      }

      // If a block is "dirty", we need to save it before continuing.
      // TODO: Implement this for transitions too
      if (context.getters[ProjectViewGetters.selectedBlockDirty]) {
        await context.dispatch(`project/editBlockPane/${EditBlockActions.saveBlock}`, null, { root: true });
      }

      // Skip everything else because we're in demo mode.
      if (context.state.isInDemoMode) {
        return;
      }

      context.commit(ProjectViewMutators.isSavingProject, true);

      const projectJson = wrapJson(context.state.openedProject);
      const configJson = wrapJson(context.state.openedProjectConfig);

      if (!projectJson || !configJson) {
        console.error('Unable to serialize project into JSON data');
        return;
      }

      const response = await makeApiRequest<SaveProjectRequest, SaveProjectResponse>(API_ENDPOINT.SaveProject, {
        diagram_data: projectJson,
        project_id: context.state.openedProject.project_id,
        config: configJson,
        // We can set this to false and let the backend bump versions for us. :)
        version: false // context.state.openedProjectConfig.version + 1
      });

      if (!response || !response.success) {
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

      const latestDeploymentResponse = await makeApiRequest<
        GetLatestProjectDeploymentRequest,
        GetLatestProjectDeploymentResponse
      >(API_ENDPOINT.GetLatestProjectDeployment, {
        project_id: openedProject.project_id
      });

      context.commit(ProjectViewMutators.setLatestDeploymentState, latestDeploymentResponse);
    },
    async [ProjectViewActions.importProjectRepo](context) {
      if (!context.state.openedProject || !context.state.openedProjectConfig) {
        console.error('no project open or no project config');
        return;
      }

      if (!context.state.openedProjectConfig.project_repo) {
        console.error('no project repo configured');
        return;
      }

      const project = await compileProjectRepo(
        context.state.openedProject.project_id,
        context.state.openedProjectConfig.project_repo
      );

      const config = context.state.openedProjectConfig;

      context.commit(ProjectViewMutators.resetState);

      const params: OpenProjectMutation = {
        project: project,
        config: config,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },
    async [ProjectViewActions.saveToProjectRepo](context) {
      if (!context.state.openedProject || !context.state.openedProjectConfig) {
        console.error('no project open or no project config');
        return;
      }

      if (!context.state.openedProjectConfig.project_repo) {
        console.error('no project repo configured');
        return;
      }

      // TODO prompt user to enter name
      const branchName = slugify(generateStupidName()).toLowerCase();

      const repoProject = context.state.openedProject;
      const projectRepoURL = context.state.openedProjectConfig.project_repo;

      await saveProjectToRepo(repoProject, projectRepoURL, branchName).catch(e => console.error(e));
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

      if (
        !context.state.openedProject ||
        !context.state.openedProjectConfig ||
        !context.getters[ProjectViewGetters.canDeployProject]
      ) {
        console.error('Tried to deploy project but should not have been enabled');
        return;
      }

      if (context.getters[ProjectViewGetters.canSaveProject]) {
        await context.dispatch(ProjectViewActions.saveProject);

        // If still dirty, throw an error.
        if (context.getters[ProjectViewGetters.canSaveProject]) {
          await handleDeploymentError('Project could not be saved before the deploy. Check for errors.');
          return;
        }
      }

      context.commit(ProjectViewMutators.isDeployingProject, true);

      const openedProject = context.state.openedProject as RefineryProject;

      if (!context.state.latestDeploymentState) {
        return await handleDeploymentError('Missing latest project deployment information');
      }

      if (context.state.latestDeploymentState.result && context.state.latestDeploymentState.result.deployment_json) {
        try {
          await teardownProject(
            openedProject.project_id,
            context.state.latestDeploymentState.result.deployment_json.workflow_states
          );
          // Reset the state
          await context.dispatch(`deployment/${DeploymentViewActions.resetDeploymentState}`, null, { root: true });
        } catch (e) {
          console.error(e);
          await handleDeploymentError('Unable to delete existing deployment.');
          return;
        }
      }

      try {
        const deploymentExceptions = await deployProject({
          project: openedProject,
          projectConfig: context.state.openedProjectConfig
        });

        if (deploymentExceptions) {
          context.commit(ProjectViewMutators.setDeploymentError, deploymentExceptions);
          return;
        }
      } catch (e) {
        return await handleDeploymentError(e.message);
      } finally {
        context.commit(ProjectViewMutators.isDeployingProject, false);
      }

      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);

      context.commit(ProjectViewMutators.setDeploymentError, null);

      // Updates the latest deployment state so the "Deployment" tab is kept updated.
      await context.dispatch(ProjectViewActions.fetchLatestDeploymentState);

      // Update project config
      await context.dispatch(ProjectViewActions.loadProjectConfig);

      router.push({
        name: 'deployment',
        params: {
          projectId: openedProject.project_id
        }
      });

      await createToast(context.dispatch, {
        title: 'Project Deployed',
        content: `Successfully created deployment for project: ${openedProject.name}`,
        variant: ToastVariant.success
      });
    },
    async [ProjectViewActions.loadProjectConfig](context) {
      const project = context.state.openedProject;

      if (!project) {
        console.error('Somehow you tried to load the project config without having an opened project!');
        return;
      }

      context.commit(ProjectViewMutators.isLoadingProject, true);
      const projectConfigResult = await makeApiRequest<GetProjectConfigRequest, GetProjectConfigResponse>(
        API_ENDPOINT.GetProjectConfig,
        {
          project_id: project.project_id
        }
      );

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

      const params: OpenProjectMutation = {
        project: null,
        config: projectConfig,
        markAsDirty: false
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
      context.commit(ProjectViewMutators.isLoadingProject, false);
    },
    async [ProjectViewActions.showDeploymentPane](context) {
      if (!context.state.openedProject || !context.getters[ProjectViewGetters.canDeployProject]) {
        console.error('Tried to show deployment pane with missing state');
        return;
      }

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

    async [ProjectViewActions.saveSelectedResource](context) {
      if (context.getters.selectedResourceDirty && !context.getters[ProjectViewGetters.canSaveProject]) {
        await createToast(context.dispatch, {
          title: 'Invalid Block State Detected',
          content: 'Please fix or discard changes to block before selecting another resource.',
          variant: ToastVariant.warning
        });
        throw new Error('Invalid block state detected, throwing to prevent further log from firing.');
      }

      // If a block is "dirty", we need to save it before continuing.
      if (context.getters[ProjectViewGetters.selectedBlockDirty]) {
        await saveEditBlockToProject();
      }

      await context.dispatch(`editBlockPane/${EditBlockActions.tryToCloseBlock}`);

      // Dang man, we're gonna have to rewrite these transitions at some point. This architecture is madness!
      if (
        context.rootGetters[`project/editTransitionPane/isStateDirty`] &&
        context.state.newTransitionTypeSpecifiedInEditFlow
      ) {
        await context.dispatch(
          `editTransitionPane/${EditTransitionActions.changeTransitionType}`,
          context.state.newTransitionTypeSpecifiedInEditFlow
        );
      }

      if (context.getters.selectedResourceDirty) {
        const message = 'Please save or discard changes before selecting another resource.';
        await createToast(context.dispatch, {
          title: 'Unsaved Block Detected',
          content: message,
          variant: ToastVariant.warning
        });
        throw new Error(message);
      }
    },

    async [ProjectViewActions.clearSelection](context) {
      if (context.state.isAddingTransitionCurrently) {
        return;
      }

      try {
        await context.dispatch(ProjectViewActions.saveSelectedResource);
      } catch (e) {
        // Not possible to continue because the project is in an invalid state.
        return;
      }

      context.commit(ProjectViewMutators.selectedResource, null);
      await context.dispatch(ProjectViewActions.updateAvailableTransitions);
      await context.dispatch(ProjectViewActions.updateAvailableEditTransitions);
    },
    async [ProjectViewActions.completeAddingSharedFileToCodeBlock](context, nodeId: string) {
      const sharedFile = await EditSharedFilePaneModule.getSharedFile();

      if (sharedFile === null) {
        console.error('Shared file was null when attempting to add it to a block, quitting out!');
        return;
      }

      const addSharedFileLinkArgs: AddSharedFileLinkArguments = {
        file_id: sharedFile.id,
        node: nodeId,
        path: ''
      };

      // Complete adding the shared file link
      await context.dispatch(ProjectViewActions.addSharedFileLink, addSharedFileLinkArgs);

      // Turn off the adding shared file to code block mode.
      await context.dispatch(ProjectViewActions.setIsAddingSharedFileToCodeBlock, false);

      // Return to the previous panel
      await EditSharedFilePaneModule.navigateToPreviousSharedFilesPane();
    },
    async [ProjectViewActions.addSharedFileLink](context, addSharedFileLinkArgs: AddSharedFileLinkArguments) {
      // This should not happen
      if (!context.state.openedProject) {
        console.error('Adding shared file but not project was opened');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      // Refused to add a shared file to a Code Block that already has one.
      const existingFileLinks = openedProject.workflow_file_links.filter(workflow_file_link => {
        return (
          workflow_file_link.node === addSharedFileLinkArgs.node &&
          workflow_file_link.file_id == addSharedFileLinkArgs.file_id
        );
      });

      if (existingFileLinks.length > 0) {
        await createToast(context.dispatch, {
          title: 'Error, this file is already linked to this code block!',
          content: 'You have already added this shared file to this code block.',
          variant: ToastVariant.danger
        });
        return;
      }

      const newSharedFileLink: WorkflowFileLink = {
        id: uuid(),
        file_id: addSharedFileLinkArgs.file_id,
        node: addSharedFileLinkArgs.node,
        type: WorkflowFileLinkType.SHARED_FILE_LINK,
        version: '1.0.0',
        path: addSharedFileLinkArgs.path
      };

      const newProject: RefineryProject = {
        ...openedProject,
        workflow_file_links: [...openedProject.workflow_file_links, newSharedFileLink]
      };

      const params: OpenProjectMutation = {
        project: newProject,
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);

      return newSharedFileLink;
    },
    async [ProjectViewActions.selectNode](context, nodeId: string) {
      if (context.state.isAddingSharedFileToCodeBlock) {
        await context.dispatch(ProjectViewActions.completeAddingSharedFileToCodeBlock, nodeId);
        return;
      }

      if (context.state.isAddingTransitionCurrently) {
        await context.dispatch(ProjectViewActions.completeTransitionAdd, nodeId);
        return;
      }

      if (!context.state.openedProject) {
        console.error('Attempted to select node without opened project', nodeId);
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }

      try {
        await context.dispatch(ProjectViewActions.saveSelectedResource);
      } catch (e) {
        // Not possible to continue because the project is in an invalid state.
        return;
      }

      // TODO: Is this necessary?
      await context.dispatch(ProjectViewActions.resetPanelStates);

      const rawNode = getNodeDataById(context.state.openedProject, nodeId);

      if (!rawNode) {
        console.error('No node was found with id', nodeId);
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }

      const node = deepJSONCopy(rawNode);

      context.commit(ProjectViewMutators.selectedResource, node.id);

      await context.dispatch(ProjectViewActions.updateAvailableTransitions);

      // Opens up the Edit block pane
      await context.dispatch(ProjectViewActions.openRightSidebarPane, SIDEBAR_PANE.editBlock);
      await context.dispatch(`editBlockPane/${EditBlockActions.selectCurrentlySelectedProjectNode}`);
    },
    async [ProjectViewActions.selectEdge](context, edgeId: string) {
      if (!context.state.openedProject) {
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }

      try {
        await context.dispatch(ProjectViewActions.saveSelectedResource);
      } catch (e) {
        // Not possible to continue because the project is in an invalid state.
        return;
      }

      // I don't have a good answer for this, but my best guess is that
      // just having a reset pane state call for edge and node selection is
      // the best way to go about this? This may cause users to lose their
      // current state though :( so maybe detect it and stop it?
      await context.dispatch(ProjectViewActions.resetPanelStates);

      // await context.dispatch(ProjectViewActions.clearSelection);

      const edges = context.state.openedProject.workflow_relationships.filter(e => e.id === edgeId);

      if (edges.length === 0) {
        console.error('No edge was found with id', edgeId);
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }

      const selectedEdge = edges[0];

      context.commit(ProjectViewMutators.selectedResource, selectedEdge.id);

      // If we're editing an "IF" transition, skip directly to the secondary transition panel
      if (selectedEdge.type === WorkflowRelationshipType.IF) {
        await context.dispatch(ProjectViewActions.selectTransitionTypeToEdit, WorkflowRelationshipType.IF);
      }

      await context.dispatch(DeploymentViewActions.openRightSidebarPane, SIDEBAR_PANE.editTransition);
      await context.dispatch(ProjectViewActions.updateAvailableEditTransitions);
      await context.dispatch(`editTransitionPane/${EditTransitionActions.selectCurrentlySelectedProjectEdge}`);
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

      const newTransition = createNewTransition(
        context.state.newTransitionTypeSpecifiedInAddFlow,
        context.state.selectedResource,
        nodeId,
        context.state.ifExpression
      );

      if (context.state.openedProject === null) {
        console.error("Something odd has occurred, you're trying to add a transition with no project opened!");
        await context.dispatch(ProjectViewActions.cancelAddingTransition);
        return;
      }

      // Ensure we have a valid transition
      const toNode = getNodeDataById(context.state.openedProject, nodeId);
      const fromNode = getNodeDataById(context.state.openedProject, context.state.selectedResource);

      if (toNode === null || fromNode === null) {
        console.error('Something odd has occurred, you have an unknown node selected for this transition!');
        await context.dispatch(ProjectViewActions.cancelAddingTransition);
        return;
      }

      // Validate the transition is possible. e.g. Not Code Block -> Timer Block
      if (!isValidTransition(fromNode, toNode)) {
        await createToast(context.dispatch, {
          title: 'Error, invalid transition!',
          content:
            'That is not a valid transition, please select one of the flashing blocks to add a valid transition.',
          variant: ToastVariant.danger
        });
        return;
      }

      await context.dispatch(ProjectViewActions.addTransition, newTransition);
      await context.dispatch(ProjectViewActions.cancelAddingTransition);
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);
      // await context.dispatch(ProjectViewActions.selectEdge, newTransition.id);

      // TODO: Open right sidebar pane
    },
    async [ProjectViewActions.openLeftSidebarPane](context, leftSidebarPaneType: SIDEBAR_PANE) {
      // If it's the Shared File pane we need to hook it to add it to the history.
      if (leftSidebarPaneType === SIDEBAR_PANE.sharedFiles) {
        await context.dispatch(`editSharedFile/setCurrentShareFilePaneHistory`, leftSidebarPaneType, { root: true });
        await context.dispatch(`sharedFiles/resetPane`, null, { root: true });
      }

      if (context.state.isAddingTransitionCurrently) {
        // TODO: Add a shake or something? Tell the user that it's bjorked.
        return;
      }

      if (context.state.isInDemoMode && demoModeBlacklist.includes(leftSidebarPaneType)) {
        await context.dispatch(`unauthViewProject/promptDemoModeSignup`, true, { root: true });
        return;
      }

      // Special case because Mandatory and I agreed that having a pane pop out is annoying af
      if (leftSidebarPaneType === SIDEBAR_PANE.saveProject) {
        await context.dispatch(ProjectViewActions.saveProject);
        return;
      }

      if (leftSidebarPaneType === SIDEBAR_PANE.importProjectRepo) {
        await context.dispatch(ProjectViewActions.importProjectRepo);
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

      if (leftSidebarPaneType === SIDEBAR_PANE.exportProject) {
        await context.dispatch(ProjectViewActions.generateShareUrl);
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
    // TODO: De-duplicate this logic across panes... It is nasty.
    async [ProjectViewActions.openRightSidebarPane](context, paneType: SIDEBAR_PANE) {
      if (context.state.isAddingTransitionCurrently) {
        // TODO: Add a shake or something? Tell the user that it's bjorked.
        return;
      }

      if (context.state.isInDemoMode && demoModeBlacklist.includes(paneType)) {
        await context.dispatch(`unauthViewProject/promptDemoModeSignup`, true, { root: true });
        return;
      }

      // Special case because Mandatory and I agreed that having a pane pop out is annoying af
      if (paneType === SIDEBAR_PANE.saveProject) {
        await context.dispatch(ProjectViewActions.saveProject);
        return;
      }

      if (paneType === SIDEBAR_PANE.importProjectRepo) {
        await context.dispatch(ProjectViewActions.importProjectRepo);
        return;
      }

      // TODO: Somehow fire a callback on each left pane so that it can reset itself?
      // Using a watcher seems gross... A plugin could work but that feels a little bit too "loose".
      // Better would be a map of Type -> Callback probably? Just trigger other actions to fire?
      // Or have the ProjectEditorLeftPaneContainer fire a callback on the child component?
      // That also feels wrong because it violates to "one direction" principal, in a way.
      context.commit(ProjectViewMutators.setRightSidebarPane, paneType);

      if (paneType === SIDEBAR_PANE.exportProject) {
        await context.dispatch(ProjectViewActions.generateShareUrl);
        return;
      }
    },
    async [ProjectViewActions.resetPanelStates](context) {
      context.commit(ProjectViewMutators.selectedResource, null);
      context.commit(ProjectViewMutators.setSelectedBlockIndex, null);

      context.commit(ProjectViewMutators.setValidTransitions, null);
      context.commit(ProjectViewMutators.setValidEditTransitions, null);

      await context.dispatch(ProjectViewActions.cancelAddingTransition);
      await context.dispatch(ProjectViewActions.cancelEditingTransition);

      // TODO: Add "close all panes"
      // await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);
      // await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.right);
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
      // If the block is saved
      if (rawBlockType === savedBlockType) {
        await context.dispatch(ProjectViewActions.openLeftSidebarPane, SIDEBAR_PANE.addSavedBlock);
        return;
      }

      const addBlockWithType = async (addBlockArgs: AddBlockArguments) =>
        await context.dispatch(ProjectViewActions.addIndividualBlock, addBlockArgs);

      const newlyAddedBlock = await addBlockWithType({
        rawBlockType,
        selectAfterAdding: true
      });

      // If the block is an API Endpoint block we check if they already have an API endpoint
      // in the project. If not we will automatically add the API endpoint and API response block
      // connected to a Code Block
      if (rawBlockType === WorkflowStateType.API_ENDPOINT) {
        await addAPIBlocksToProject(newlyAddedBlock, context.state, context.dispatch);
      }
    },
    async [ProjectViewActions.addSharedFile](context, addSharedFileArgs: AddSharedFileArguments) {
      // This should not happen
      if (!context.state.openedProject) {
        console.error('Adding shared file but not project was opened');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      const newSharedFile: WorkflowFile = {
        id: uuid(),
        type: WorkflowFileType.SHARED_FILE,
        version: '1.0.0',
        name: addSharedFileArgs.name,
        body: addSharedFileArgs.body
      };

      const newProject: RefineryProject = {
        ...openedProject,
        workflow_files: [...openedProject.workflow_files, newSharedFile]
      };

      const params: OpenProjectMutation = {
        project: newProject,
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);

      return newSharedFile;
    },
    async [ProjectViewActions.saveSharedFile](context, sharedFile: WorkflowFile) {
      if (!context.state.openedProject) {
        console.error("No project is open so we can't save the shared file!");
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      const newProject: RefineryProject = {
        ...openedProject,
        workflow_files: [
          ...openedProject.workflow_files.filter(workflowFile => {
            return workflowFile.id !== sharedFile.id;
          }),
          <WorkflowFile>deepJSONCopy(sharedFile)
        ]
      };

      const params: OpenProjectMutation = {
        project: newProject,
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },
    async [ProjectViewActions.deleteSharedFile](context, sharedFile: WorkflowFile) {
      if (!context.state.openedProject) {
        console.error("No project is open so we can't delete the shared file!");
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      const newProject: RefineryProject = {
        ...openedProject,
        workflow_files: [
          ...openedProject.workflow_files.filter(workflowFile => {
            return workflowFile.id !== sharedFile.id;
          })
        ],
        workflow_file_links: [
          ...openedProject.workflow_file_links.filter(workflowFileLink => {
            return workflowFileLink.file_id !== sharedFile.id;
          })
        ]
      };

      const params: OpenProjectMutation = {
        project: newProject,
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },
    async [ProjectViewActions.deleteSharedFileLink](context, sharedFileLink: WorkflowFileLink) {
      if (!context.state.openedProject) {
        console.error("No project is open so we can't delete the shared file!");
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      const newProject: RefineryProject = {
        ...openedProject,
        workflow_file_links: [
          ...openedProject.workflow_file_links.filter(workflowFileLink => {
            return workflowFileLink.id !== sharedFileLink.id;
          })
        ]
      };

      const params: OpenProjectMutation = {
        project: newProject,
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },
    async [ProjectViewActions.addIndividualBlock](context, addBlockArgs: AddBlockArguments) {
      // This should not happen
      if (!context.state.openedProject) {
        console.error('Adding block but not project was opened');
        return;
      }

      const openedProject = context.state.openedProject as RefineryProject;

      // Catches the case of "unknown" block types causing craziness later!
      if (!Object.values(WorkflowStateType).includes(addBlockArgs.rawBlockType as WorkflowStateType)) {
        console.error('Unknown block type requested to be added!', addBlockArgs.rawBlockType);
        return;
      }

      const blockType = addBlockArgs.rawBlockType as WorkflowStateType;

      // Special casing for the API Response block which should never
      // have it's name changed. Certain blocks will likely make sense for this.
      const immutable_names: WorkflowStateType[] = [WorkflowStateType.API_GATEWAY_RESPONSE];

      let newBlockName: string = `Untitled ${blockTypeToImageLookup[blockType].name}`;
      if (immutable_names.includes(blockType)) {
        newBlockName = blockTypeToImageLookup[blockType].name;
      }

      // Set configured new block defaults
      if (blockType === WorkflowStateType.LAMBDA && context.state.openedProjectConfig) {
        const defaultLanguage = context.state.openedProjectConfig.default_language || SupportedLanguage.NODEJS_8;
        addBlockArgs.customBlockProperties = Object.assign({}, addBlockArgs.customBlockProperties, {
          language: defaultLanguage,
          code: DEFAULT_LANGUAGE_CODE[defaultLanguage],

          // if customBlockProperties define language and code, then override them here
          ...addBlockArgs.customBlockProperties
        });
      }

      const newBlock = createNewBlock(blockType, newBlockName, addBlockArgs.customBlockProperties);

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

      await context.dispatch(ProjectViewActions.updateProject, params);
      if (addBlockArgs.selectAfterAdding) {
        await context.dispatch(ProjectViewActions.selectNode, newBlock.id);
        await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.left);
      }

      return newBlock;
    },
    async [ProjectViewActions.changeExistingTransition](
      context,
      ChangeTransitionArgumentsValue: ChangeTransitionArguments
    ) {
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
          workflowRelationship.expression = '';

          if (workflowRelationship.type === WorkflowRelationshipType.IF) {
            workflowRelationship.expression = context.state.ifExpression;
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

      const otherTransitions = deepJSONCopy(
        openedProject.workflow_relationships.filter(wfs => wfs.id !== transition.id)
      );

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
          workflow_states: otherBlocks,
          // Remove the file links as well.
          workflow_file_links: [
            ...openedProject.workflow_file_links.filter(workflowFileLink => {
              return workflowFileLink.node !== node.id;
            })
          ]
        },
        config: null,
        markAsDirty: true
      };

      await context.dispatch(ProjectViewActions.updateProject, params);
    },
    async [ProjectViewActions.setIsAddingSharedFileToCodeBlock](context, isAdding: boolean) {
      context.commit(ProjectViewMutators.setIsAddingSharedFileToCodeBlock, isAdding);
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
      // await context.dispatch(ProjectViewActions.selectEdge, newTransition.id);
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
      await context.dispatch(ProjectViewActions.ifDropdownSelection, IfDropDownSelectionType.DEFAULT);
      await context.dispatch(ProjectViewActions.setIfExpression, '');
      context.commit(ProjectViewMutators.setAddingTransitionStatus, false);
      context.commit(ProjectViewMutators.setAddingTransitionType, null);
    },
    async [ProjectViewActions.cancelEditingTransition](context) {
      await context.dispatch(ProjectViewActions.ifDropdownSelection, IfDropDownSelectionType.DEFAULT);
      await context.dispatch(ProjectViewActions.setIfExpression, '');
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

        const ifExpressionValue =
          selectedEdge.expression === '' ? IfDropdownSelectionExpressionValues.DEFAULT : selectedEdge.expression;

        // Set the ifExpression to reflect the selected transition
        await context.dispatch(ProjectViewActions.setIfExpression, ifExpressionValue);

        context.commit(ProjectViewMutators.setEditingTransitionStatus, true);
        context.commit(ProjectViewMutators.setEditingTransitionType, transitionType);
        return;
      }
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.right);

      // Change the transition to the new type
      await context.dispatch(`editTransitionPane/${EditTransitionActions.changeTransitionType}`, transitionType);
      await context.dispatch(ProjectViewActions.cancelEditingTransition);
    },
    async [ProjectViewActions.selectTransitionTypeToAdd](context, transitionType: WorkflowRelationshipType) {
      await context.dispatch(ProjectViewActions.closePane, PANE_POSITION.right);
      context.commit(ProjectViewMutators.setAddingTransitionStatus, true);
      context.commit(ProjectViewMutators.setAddingTransitionType, transitionType);

      if (transitionType === WorkflowRelationshipType.IF) {
        await context.dispatch(ProjectViewActions.setIfExpression, IfDropdownSelectionExpressionValues.DEFAULT);
      }
    },
    async [ProjectViewActions.generateShareUrl](context) {
      if (!context.rootState.user.authenticated) {
        // Check the current authentication status before deciding which URL to export.
        await context.dispatch(`user/${UserActions.fetchAuthenticationState}`, null, { root: true });

        // If we're double sure we're not authenticated... Bail out.
        if (!context.rootState.user.authenticated) {
          return;
        }
      }

      if (!context.state.openedProject) {
        console.error('Missing project to be exported');
        return;
      }

      const { project_id, ...rest } = context.state.openedProject;

      context.commit(ProjectViewMutators.setIsCreatingShortlink, true);

      const shortLink = await createShortlink(rest);

      context.commit(ProjectViewMutators.setIsCreatingShortlink, false);

      context.commit(ProjectViewMutators.setShortlinkUrl, shortLink);
    }
  }
};

export default ProjectViewModule;
