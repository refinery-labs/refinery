import { Module } from 'vuex';
import { DeploymentViewState, RootState } from '@/store/store-types';
import { generateCytoscapeElements, generateCytoscapeStyle } from '@/lib/refinery-to-cytoscript-converter';
import { LayoutOptions } from 'cytoscape';
import cytoscape from '@/components/CytoscapeGraph';
import {
  DeploymentViewActions,
  DeploymentViewGetters,
  DeploymentViewMutators,
  ProjectViewActions
} from '@/constants/store-constants';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import {
  GetLatestProjectDeploymentRequest,
  GetLatestProjectDeploymentResponse,
  GetLatestProjectDeploymentResult
} from '@/types/api-types';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import { createToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';
import router from '@/router';
import { getNodeDataById } from '@/utils/project-helpers';
import { ViewBlockActions } from '@/store/modules/panes/view-block-pane';
import { ViewTransitionActions } from '@/store/modules/panes/view-transition-pane';
import {
  DeploymentExecutionsActions,
  DeploymentExecutionsGetters,
  DeploymentExecutionsMutators
} from '@/store/modules/panes/deployment-executions-pane';
import { teardownProject } from '@/store/fetchers/api-helpers';
import { deepJSONCopy } from '@/lib/general-utils';
import { CyElements, CyStyle } from '@/types/cytoscape-types';
import { DemoWalkthroughStoreModule } from '@/store';

const moduleState: DeploymentViewState = {
  openedDeployment: null,
  openedDeploymentId: null,
  openedDeploymentProjectId: null,
  openedDeploymentTimestamp: null,

  destroyModalVisible: false,
  isDestroyingDeployment: false,

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
  state: deepJSONCopy(moduleState),
  getters: {
    [DeploymentViewGetters.hasValidDeployment]: state => state.openedDeployment !== null,
    [DeploymentViewGetters.getSelectedBlock]: state => {
      if (!state.openedDeployment || !state.selectedResource) {
        return null;
      }

      // Will only return a Block and automatically excludes edges
      return getNodeDataById(state.openedDeployment, state.selectedResource);
    }
  },
  mutations: {
    [DeploymentViewMutators.resetState](state) {
      // TODO: Turn this into a helper function.
      // @ts-ignore
      Object.keys(moduleState).forEach(key => (state[key] = deepJSONCopy(moduleState[key])));
    },
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

    [DeploymentViewMutators.setDestroyDeploymentModalVisibility](state, value: boolean) {
      state.destroyModalVisible = value;
    },
    [DeploymentViewMutators.setIsDestroyingDeployment](state, value: boolean) {
      state.isDestroyingDeployment = value;
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
      const freshDeploymentView = context.state.openedDeployment === null;

      // If we don't have data, then block the UI until we do.
      if (freshDeploymentView) {
        context.commit(DeploymentViewMutators.isLoadingDeployment, true);

        // Only wait for this data if we don't have it...
        await context.dispatch(DeploymentViewActions.loadDeploymentData, projectId);
      } else {
        // Don't await this call so that the UI is snappy.
        // Refresh the data anyway though just in case something has changed.
        context.dispatch(DeploymentViewActions.loadDeploymentData, projectId);
      }

      context.commit(DeploymentViewMutators.isLoadingDeployment, false);

      if (freshDeploymentView) {
        await context.dispatch(DeploymentViewActions.openViewExecutionsPane);
      }

      // Activates the job to watch for new execution data.
      context.dispatch(`deploymentExecutions/${DeploymentExecutionsActions.activatePane}`, null, {
        root: true
      });
    },
    async [DeploymentViewActions.loadDeploymentData](context, projectId: string) {
      const handleError = async (message: string) => {
        context.commit(DeploymentViewMutators.isLoadingDeployment, false);
        console.error(message);
        await createToast(context.dispatch, {
          title: 'View Deployment Error',
          content: message,
          variant: ToastVariant.danger
        });
      };

      let deploymentResponse: GetLatestProjectDeploymentResponse | null;
      if (!DemoWalkthroughStoreModule.showingDemoWalkthrough) {
        deploymentResponse = await makeApiRequest<
          GetLatestProjectDeploymentRequest,
          GetLatestProjectDeploymentResponse
        >(API_ENDPOINT.GetLatestProjectDeployment, {
          project_id: projectId
        });

        if (!deploymentResponse || !deploymentResponse.success || !deploymentResponse.result) {
          await handleError('Unable to open project, missing deployment data');
          return;
        }
      } else {
        deploymentResponse = DemoWalkthroughStoreModule.mockGetLatestProjectDeployment;
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
    },
    async [DeploymentViewActions.destroyDeployment](context) {
      const handleError = async (message: string) => {
        context.commit(DeploymentViewMutators.setIsDestroyingDeployment, false);
        console.error('Unable to destroy deployment', message);
        await createToast(context.dispatch, {
          title: 'Destroy Deployment Error',
          content: message,
          variant: ToastVariant.danger
        });
      };

      if (!context.state.openedDeploymentProjectId || !context.state.openedDeployment) {
        await handleError('Must have valid opened project to initiate Destroy Deployment');
        return;
      }

      context.commit(DeploymentViewMutators.setIsDestroyingDeployment, true);

      try {
        await teardownProject(context.state.openedDeploymentProjectId, context.state.openedDeployment.workflow_states);
      } catch (e) {
        await handleError(e.message);
        return;
      }

      context.commit(DeploymentViewMutators.setIsDestroyingDeployment, false);
      await createToast(context.dispatch, {
        title: 'Deployment Deleted Successfully',
        content: 'The deployment was successfully removed from production. Redirecting to the project view now...',
        variant: ToastVariant.success
      });

      // Updates the latest deployment state so the "Deployment" tab is kept updated.
      await context.dispatch(`project/${ProjectViewActions.fetchLatestDeploymentState}`, null, { root: true });

      router.push({
        name: 'project',
        params: {
          projectId: context.state.openedDeploymentProjectId
        }
      });

      // Destroy the state because it's donezo now.
      await context.dispatch(DeploymentViewActions.resetDeploymentState);
    },

    async [DeploymentViewActions.clearSelection](context) {
      context.commit(DeploymentViewMutators.selectedResource, null);

      // Close the selected pane pane
      await context.dispatch(DeploymentViewActions.closePane, PANE_POSITION.right);

      await context.dispatch(`viewBlock/${ViewBlockActions.selectCurrentlySelectedProjectNode}`, null, { root: true });
    },
    async [DeploymentViewActions.selectNode](context, nodeId: string) {
      if (!context.state.openedDeployment) {
        console.error('Attempted to select node without opened deployment', nodeId);
        context.commit(DeploymentViewMutators.selectedResource, null);
        return;
      }

      const rawNode = getNodeDataById(context.state.openedDeployment, nodeId);

      if (!rawNode) {
        console.error('No node was found with id', nodeId);
        context.commit(DeploymentViewMutators.selectedResource, null);
        return;
      }

      const node = deepJSONCopy(rawNode);

      context.commit(DeploymentViewMutators.selectedResource, node.id);

      await context.dispatch(`viewBlock/${ViewBlockActions.selectCurrentlySelectedProjectNode}`, null, { root: true });

      const doesBlockHaveExecutions: boolean =
        context.rootGetters[`deploymentExecutions/${DeploymentExecutionsGetters.doesSelectedBlockHaveExecutions}`];

      const paneToOpen = doesBlockHaveExecutions ? SIDEBAR_PANE.viewDeployedBlockLogs : SIDEBAR_PANE.viewDeployedBlock;

      // TODO: Refactor this log handling logic so that this isn't leaking into another store.
      // Kick off grabbing the logs
      if (doesBlockHaveExecutions) {
        // Clear the currently selected log
        context.commit(`deploymentExecutions/${DeploymentExecutionsMutators.setSelectedBlockExecutionLog}`, null, {
          root: true
        });

        // Kick off the call to fetch logs for the current block -- which will select a log too.
        context.dispatch(`deploymentExecutions/${DeploymentExecutionsActions.fetchLogsForSelectedBlock}`, null, {
          root: true
        });
      }

      await context.dispatch(DeploymentViewActions.openRightSidebarPane, paneToOpen);
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

      await context.dispatch(`viewBlock/${ViewBlockActions.selectCurrentlySelectedProjectNode}`, null, { root: true });

      await context.dispatch(DeploymentViewActions.openRightSidebarPane, SIDEBAR_PANE.viewDeployedTransition);

      await context.dispatch(`viewTransition/${ViewTransitionActions.selectCurrentlySelectedDeploymentEdge}`, null, {
        root: true
      });
    },
    async [DeploymentViewActions.openViewExecutionsPane](context) {
      await context.dispatch(DeploymentViewActions.openLeftSidebarPane, SIDEBAR_PANE.viewExecutions);
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
      context.commit(DeploymentViewMutators.resetState);
      context.commit(`deploymentExecutions/${DeploymentExecutionsMutators.resetPane}`, null, { root: true });
    }
  }
};

export default DeploymentViewModule;
