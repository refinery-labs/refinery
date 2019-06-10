import {Module} from 'vuex';
import {DeploymentViewState, RootState} from '@/store/store-types';
import {
  CyElements,
  CyStyle,
} from '@/types/graph';
import {generateCytoscapeElements, generateCytoscapeStyle} from '@/lib/refinery-to-cytoscript-converter';
import {LayoutOptions} from 'cytoscape';
import cytoscape from '@/components/CytoscapeGraph';
import {DeploymentViewActions, DeploymentViewGetters, DeploymentViewMutators} from '@/constants/store-constants';
import {makeApiRequest} from '@/store/fetchers/refinery-api';
import {API_ENDPOINT} from '@/constants/api-constants';
import {
  GetLatestProjectDeploymentRequest,
  GetLatestProjectDeploymentResponse, GetLatestProjectDeploymentResult,
} from '@/types/api-types';
import {PANE_POSITION, SIDEBAR_PANE} from '@/types/project-editor-types';
import {EditBlockActions} from '@/store/modules/panes/edit-block-pane';
import {createToast} from '@/utils/toasts-utils';
import {ToastVariant} from '@/types/toasts-types';

const moduleState: DeploymentViewState = {
  openedDeployment: null,
  openedDeploymentId: null,
  openedDeploymentProjectId: null,
  openedDeploymentTimestamp: null,

  isLoadingDeployment: true,
  
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
  selectedBlockIndex: null
};

const DeploymentViewModule: Module<DeploymentViewState, RootState> = {
  namespaced: true,
  modules: {},
  state: moduleState,
  getters: {
    [DeploymentViewGetters.hasValidDeployment]: state => state.openedDeployment !== null
  },
  mutations: {
    [DeploymentViewMutators.setOpenedDeployment](state, deployment: GetLatestProjectDeploymentResult) {

      if (!deployment) {
        state.openedDeployment = null;
        state.openedDeploymentId = null;
        state.openedDeploymentProjectId = null;
        state.openedDeploymentTimestamp = null;
        return;
      }

      // Set these as "flat" objects in order to make Vuex state synchronization easier
      state.openedDeployment = {
        ...deployment.deployment_json,
        // Add in the missing field
        project_id: deployment.project_id
      };

      state.openedDeploymentId = deployment.id;
      state.openedDeploymentProjectId = deployment.project_id;
      state.openedDeploymentTimestamp = deployment.timestamp;
    },
    [DeploymentViewMutators.isLoadingDeployment](state, value: boolean) {
      state.isLoadingDeployment = value;
    },
    [DeploymentViewMutators.selectedResource](state, resourceId: string) {
      state.selectedResource = resourceId;
    },
    [DeploymentViewMutators.setCytoscapeElements](state, elements: CyElements) {
      state.cytoscapeElements = elements;
    },
    [DeploymentViewMutators.setCytoscapeStyle](state, stylesheet: CyStyle) {
      state.cytoscapeStyle = stylesheet;
    },
    [DeploymentViewMutators.setCytoscapeLayout](state, layout: LayoutOptions) {
      state.cytoscapeLayoutOptions = layout;
    },
    [DeploymentViewMutators.setCytoscapeConfig](state, config: cytoscape.CytoscapeOptions) {
      state.cytoscapeConfig = config;
    },

    // Pane Logic
    [DeploymentViewMutators.setLeftSidebarPane](state, leftSidebarPaneType: SIDEBAR_PANE | null) {
      state.activeLeftSidebarPane = leftSidebarPaneType;
    },
    [DeploymentViewMutators.setRightSidebarPane](state, paneType: SIDEBAR_PANE | null) {
      state.activeRightSidebarPane = paneType;
    },

    // Add New Pane
    [DeploymentViewMutators.setSelectedBlockIndex](state, selectedIndex: number | null) {
      state.selectedBlockIndex = selectedIndex;
    }
  },
  actions: {
    async [DeploymentViewActions.openDeployment](context, projectId: string) {
      const handleError = async (message: string) => {
        context.commit(DeploymentViewMutators.isLoadingDeployment, false);
        console.error(message);
        await createToast(context.dispatch, {
          title: 'View Deployment Error',
          content: message,
          variant: ToastVariant.danger
        });
      };

      context.commit(DeploymentViewMutators.isLoadingDeployment, true);

      const deploymentResponse = await makeApiRequest<GetLatestProjectDeploymentRequest, GetLatestProjectDeploymentResponse>(API_ENDPOINT.GetLatestProjectDeployment, {
        project_id: projectId
      });

      if (!deploymentResponse || !deploymentResponse.success || !deploymentResponse.result) {
        await handleError('Unable to open project, missing deployment data');
        return;
      }

      context.commit(DeploymentViewMutators.setOpenedDeployment, deploymentResponse.result);

      if (!context.state.openedDeployment) {
        await handleError('Unable to open project, unknown state');
        return;
      }

      const elements = generateCytoscapeElements(context.state.openedDeployment);

      const stylesheet = generateCytoscapeStyle();

      context.commit(DeploymentViewMutators.setCytoscapeElements, elements);
      context.commit(DeploymentViewMutators.setCytoscapeStyle, stylesheet);

      context.commit(DeploymentViewMutators.isLoadingDeployment, false);
    },

    async [DeploymentViewActions.clearSelection](context) {
      context.commit(DeploymentViewMutators.selectedResource, null);
    },
    async [DeploymentViewActions.selectNode](context, nodeId: string) {

      if (!context.state.openedDeployment) {
        console.error('Attempted to select node without opened deployment', nodeId);
        context.commit(DeploymentViewMutators.selectedResource, null);
        return;
      }

      const nodes = context.state.openedDeployment.workflow_states.filter(e => e.id === nodeId);

      if (nodes.length === 0) {
        console.error('No node was found with id', nodeId);
        context.commit(DeploymentViewMutators.selectedResource, null);
        return;
      }

      const node = nodes[0];

      context.commit(DeploymentViewMutators.selectedResource, node.id);

      await context.dispatch(DeploymentViewActions.openRightSidebarPane, SIDEBAR_PANE.viewDeployedBlock);
    },
    async [DeploymentViewActions.selectEdge](context, edgeId: string) {
      if (!context.state.openedDeployment) {
        context.commit(DeploymentViewMutators.selectedResource, null);
        return;
      }

      const edges = context.state.openedDeployment.workflow_relationships.filter(e => e.id === edgeId);

      if (edges.length === 0) {
        console.error('No edge was found with id', edgeId);
        context.commit(DeploymentViewMutators.selectedResource, null);
        return;
      }

      context.commit(DeploymentViewMutators.selectedResource, edges[0].id);

      await context.dispatch(DeploymentViewActions.openRightSidebarPane, SIDEBAR_PANE.viewDeployedTransition);
    },
    async [DeploymentViewActions.openLeftSidebarPane](context, leftSidebarPaneType: SIDEBAR_PANE) {
      // TODO: Somehow fire a callback on each left pane so that it can reset itself?
      // Using a watcher seems gross... A plugin could work but that feels a little bit too "loose".
      // Better would be a map of Type -> Callback probably? Just trigger other actions to fire?
      // Or have the ProjectEditorLeftPaneContainer fire a callback on the child component?
      // That also feels wrong because it violates to "one direction" principal, in a way.
      context.commit(DeploymentViewMutators.setLeftSidebarPane, leftSidebarPaneType);

    },
    [DeploymentViewActions.closePane](context, pos: PANE_POSITION) {
      if (pos === PANE_POSITION.left) {
        context.commit(DeploymentViewMutators.setLeftSidebarPane, null);
        return;
      }

      if (pos === PANE_POSITION.right) {
        context.commit(DeploymentViewMutators.setRightSidebarPane, null);
        return;
      }

      console.error('Attempted to close unknown pane', pos);
    },
    async [DeploymentViewActions.openRightSidebarPane](context, paneType: SIDEBAR_PANE) {
      // TODO: Somehow fire a callback on each left pane so that it can reset itself?
      // Using a watcher seems gross... A plugin could work but that feels a little bit too "loose".
      // Better would be a map of Type -> Callback probably? Just trigger other actions to fire?
      // Or have the ProjectEditorLeftPaneContainer fire a callback on the child component?
      // That also feels wrong because it violates to "one direction" principal, in a way.
      context.commit(DeploymentViewMutators.setRightSidebarPane, paneType);
    },
    async [DeploymentViewActions.resetDeploymentState](context) {
      context.commit(DeploymentViewMutators.selectedResource, null);
      context.commit(DeploymentViewMutators.setCytoscapeConfig, null);
      context.commit(DeploymentViewMutators.setCytoscapeElements, null);
      context.commit(DeploymentViewMutators.setCytoscapeStyle, null);
      context.commit(DeploymentViewMutators.setSelectedBlockIndex, null);
      context.commit(DeploymentViewMutators.setOpenedDeployment, null);

      // TODO: Add "close all panes"
      await context.dispatch(DeploymentViewActions.closePane, PANE_POSITION.left);
      await context.dispatch(DeploymentViewActions.closePane, PANE_POSITION.right);
    }

  }
};

export default DeploymentViewModule;
