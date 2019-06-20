import { Module } from 'vuex';
import uuid from 'uuid/v4';
import { RootState } from '../../store-types';
import { getLogsForExecutions, getProjectExecutions } from '@/store/fetchers/api-helpers';
import { ProductionExecution } from '@/types/deployment-executions-types';
import { sortExecutions } from '@/utils/project-execution-utils';
import { ExecutionStatusType, GetProjectExecutionLogsResult } from '@/types/api-types';
import { STYLE_CLASSES } from '@/lib/cytoscape-styles';
import { deepJSONCopy } from '@/lib/general-utils';
import { timeout } from '@/utils/async-utils';

// Enums
export enum DeploymentExecutionsMutators {
  resetPane = 'resetPane',
  setIsBusy = 'setIsBusy',
  setIsFetchingMoreExecutions = 'setIsFetchingMoreExecutions',
  setProjectExecutions = 'setProjectExecutions',
  setContinuationToken = 'setContinuationToken',

  setAutoRefreshJobRunning = 'setAutoRefreshJobRunning',
  setAutoRefreshJobIterations = 'setAutoRefreshJobIterations',
  setAutoRefreshJobNonce = 'setAutoRefreshJobNonce',

  setSelectedExecutionGroup = 'setSelectedExecutionGroup',
  setExecutionGroupLogs = 'setExecutionGroupLogs',
  setSelectedExecutionIndexForNode = 'setSelectedExecutionIndexForNode'
}

export enum DeploymentExecutionsActions {
  activatePane = 'activatePane',
  getExecutionsForOpenedDeployment = 'getExecutionsForOpenedDeployment',
  openExecutionGroup = 'openExecutionGroup'
}

// Types
export interface DeploymentExecutionsPaneState {
  isBusy: boolean;
  isFetchingMoreExecutions: boolean;

  projectExecutions: { [key: string]: ProductionExecution } | null;
  continuationToken: string | null;
  autoRefreshJobRunning: boolean;
  autoRefreshJobIterations: number;
  autoRefreshJobNonce: string | null;

  selectedExecutionGroup: ProductionExecution | null;
  executionGroupLogs: { [key: string]: GetProjectExecutionLogsResult[] } | null;

  selectedExecutionIndexForNode: number;
}

// Initial State
const moduleState: DeploymentExecutionsPaneState = {
  isBusy: false,
  isFetchingMoreExecutions: false,

  projectExecutions: null,
  continuationToken: null,
  autoRefreshJobRunning: false,
  autoRefreshJobIterations: 0,
  autoRefreshJobNonce: null,

  selectedExecutionGroup: null,
  executionGroupLogs: null,

  selectedExecutionIndexForNode: 0
};

function getExecutionStatusStyleForLogs(logs: GetProjectExecutionLogsResult[]) {
  if (logs.some(ele => ele.type === ExecutionStatusType.EXCEPTION)) {
    return STYLE_CLASSES.EXECUTION_FAILURE;
  }

  if (logs.some(ele => ele.type === ExecutionStatusType.CAUGHT_EXCEPTION)) {
    return STYLE_CLASSES.EXECUTION_CAUGHT;
  }

  return STYLE_CLASSES.EXECUTION_SUCCESS;
}

interface AutoRefreshJobConfig {
  nonce: string;
  timeoutMs: number;
  maxIterations: number;
  makeRequest: () => Promise<void>;
  isStillValid: (nonce: string, iteration: number) => boolean;
}

/**
 * Job to go do something on an interval. Attempts to kill itself by leveraging callbacks for state checking.
 * @param conf Parameters for the job to function.
 * @param iterations Incremented each time and used to kill itself later by limiting max iterations.
 */
async function autoRefreshJob(conf: AutoRefreshJobConfig, iterations: number = 0) {
  if (iterations > conf.maxIterations) {
    return;
  }

  const valid = conf.isStillValid(conf.nonce, iterations);

  if (!valid) {
    return;
  }

  await conf.makeRequest();

  await timeout(conf.timeoutMs);

  await autoRefreshJob(conf, iterations + 1);
}

const DeploymentExecutionsPaneModule: Module<DeploymentExecutionsPaneState, RootState> = {
  namespaced: true,
  state: deepJSONCopy(moduleState),
  getters: {
    sortedExecutions: state => state.projectExecutions && sortExecutions(Object.values(state.projectExecutions)),
    getAllExecutionsForNode: (state, getters, rootState) => {
      if (!rootState.viewBlock.selectedNode || !state.executionGroupLogs) {
        return null;
      }

      const selectedResourceName = rootState.viewBlock.selectedNode.name;

      return state.executionGroupLogs[selectedResourceName];
    },
    getSelectedExecutionForNode: (state, getters) => {
      const allExecutions = getters.getAllExecutionsForNode;
      if (!allExecutions || allExecutions.length === 0) {
        return null;
      }

      return allExecutions[state.selectedExecutionIndexForNode] || allExecutions[0];
    },
    graphElementsWithExecutionStatus: (state, getters, rootState) => {
      if (!rootState.deployment.cytoscapeElements || !state.executionGroupLogs) {
        return null;
      }

      const logs = state.executionGroupLogs;

      const elements = rootState.deployment.cytoscapeElements;

      // Go through the graph and set each style to be of a color based on execution status
      const nodes =
        elements.nodes &&
        elements.nodes.map(element => {
          const matchingElement = logs[element.data.name];

          if (!matchingElement || matchingElement.length === 0) {
            return element;
          }

          // Sets to either a color
          const executionStatusColorClass = getExecutionStatusStyleForLogs(matchingElement);

          // Extend and return a new element
          return {
            ...element,
            classes: element.classes ? `${element.classes} ${executionStatusColorClass}` : executionStatusColorClass
          };
        });

      return {
        // Remove all null values
        nodes: nodes.filter(n => n),
        edges: elements.edges
      };
    }
  },
  mutations: {
    [DeploymentExecutionsMutators.resetPane](state) {
      // TODO: Turn this into a helper function.
      // @ts-ignore
      Object.keys(moduleState).forEach(key => (state[key] = moduleState[key]));
    },
    [DeploymentExecutionsMutators.setIsBusy](state, busy) {
      state.isBusy = busy;
    },
    [DeploymentExecutionsMutators.setIsFetchingMoreExecutions](state, isFetching) {
      state.isFetchingMoreExecutions = isFetching;
    },
    [DeploymentExecutionsMutators.setProjectExecutions](state, executions) {
      state.projectExecutions = executions;
    },
    [DeploymentExecutionsMutators.setContinuationToken](state, token) {
      state.continuationToken = token;
    },

    [DeploymentExecutionsMutators.setAutoRefreshJobRunning](state, status) {
      state.autoRefreshJobRunning = status;
    },
    [DeploymentExecutionsMutators.setAutoRefreshJobIterations](state, iteration) {
      state.autoRefreshJobIterations = iteration;
    },
    [DeploymentExecutionsMutators.setAutoRefreshJobNonce](state, nonce) {
      state.autoRefreshJobNonce = nonce;
    },

    [DeploymentExecutionsMutators.setSelectedExecutionGroup](state, group) {
      state.selectedExecutionGroup = group;
    },
    [DeploymentExecutionsMutators.setExecutionGroupLogs](state, logs) {
      state.executionGroupLogs = logs;
    },
    [DeploymentExecutionsMutators.setSelectedExecutionIndexForNode](state, index) {
      state.selectedExecutionIndexForNode = index;
    }
  },
  actions: {
    async [DeploymentExecutionsActions.activatePane](context) {
      // TODO: Set a different busy symbol when refreshing
      await context.dispatch(DeploymentExecutionsActions.getExecutionsForOpenedDeployment);

      const nonce = uuid();
      context.commit(DeploymentExecutionsMutators.setAutoRefreshJobNonce, nonce);

      // Wait for the old job to die
      if (context.state.autoRefreshJobRunning) {
        await timeout(5000);
      }

      autoRefreshJob({
        timeoutMs: 5000,
        maxIterations: 125, // 5 minutes
        nonce: nonce,
        makeRequest: async () => {
          await context.dispatch(DeploymentExecutionsActions.getExecutionsForOpenedDeployment, false);
        },
        isStillValid: (nonce, iteration) => {
          const valid = nonce === context.state.autoRefreshJobNonce;

          // If another job is running, kill this one.
          if (!valid) {
            return false;
          }

          // Only commit if we are still wanted
          context.commit(DeploymentExecutionsMutators.setAutoRefreshJobIterations, iteration);
          return true;
        }
      });
    },
    async [DeploymentExecutionsActions.getExecutionsForOpenedDeployment](context, withExistingToken?: boolean) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment) {
        console.error('Cannot retrieve logs for deployment: No deployment is opened');
        return;
      }

      // We can set this either for the module or for the sub-pane
      const statusMessageType =
        context.state.projectExecutions !== null
          ? DeploymentExecutionsMutators.setIsFetchingMoreExecutions
          : DeploymentExecutionsMutators.setIsBusy;

      context.commit(statusMessageType, true);

      // We may either use the existing token or not.
      const tokenToContinueWith = withExistingToken ? context.state.continuationToken : null;

      const executionsResponse = await getProjectExecutions(
        deploymentStore.openedDeployment.project_id,
        tokenToContinueWith
      );

      if (!executionsResponse) {
        console.error('Unable to fetch execution logs, did not receive any results from server');
        context.commit(statusMessageType, false);
        return;
      }

      // Merge against existing executions
      const executions = {
        ...(context.state.projectExecutions || {}),
        ...executionsResponse.executions
      };

      context.commit(DeploymentExecutionsMutators.setProjectExecutions, executions);
      context.commit(DeploymentExecutionsMutators.setContinuationToken, executionsResponse.continuationToken);
      context.commit(statusMessageType, false);
    },
    async [DeploymentExecutionsActions.openExecutionGroup](context, executionId: string) {
      if (!context.state.projectExecutions) {
        console.error('Attempted to open project execution without any project executions loaded');
        return;
      }

      const projectExecution = context.state.projectExecutions[executionId];

      if (!projectExecution) {
        console.error('Unable to locate execution to retrieve logs for');
        return;
      }

      context.commit(DeploymentExecutionsMutators.setIsBusy, true);

      const response = await getLogsForExecutions(projectExecution);

      context.commit(DeploymentExecutionsMutators.setSelectedExecutionGroup, projectExecution);
      context.commit(DeploymentExecutionsMutators.setExecutionGroupLogs, response);

      context.commit(DeploymentExecutionsMutators.setIsBusy, false);
    }
  }
};

export default DeploymentExecutionsPaneModule;
