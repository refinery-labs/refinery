import { Module } from 'vuex';
import { RootState } from '../../store-types';
import { getLogsForExecutions, getProjectExecutions } from '@/store/fetchers/api-helpers';
import { ProductionExecution } from '@/types/deployment-executions-types';
import { sortExecutions } from '@/utils/project-execution-utils';
import { ExecutionStatusType, GetProjectExecutionLogsResult } from '@/types/api-types';
import { STYLE_CLASSES } from '@/lib/cytoscape-styles';

// Enums
export enum DeploymentExecutionsMutators {
  setIsBusy = 'setIsBusy',
  setIsFetchingMoreExecutions = 'setIsFetchingMoreExecutions',
  setProjectExecutions = 'setProjectExecutions',
  setContinuationToken = 'setContinuationToken',

  setSelectedExecutionGroup = 'setSelectedExecutionGroup',
  setExecutionGroupLogs = 'setExecutionGroupLogs'
}

export enum DeploymentExecutionsActions {
  resetPane = 'resetPane',
  getExecutionsForOpenedDeployment = 'getExecutionsForOpenedDeployment',
  openExecutionGroup = 'openExecutionGroup'
}

// Types
export interface DeploymentExecutionsPaneState {
  isBusy: boolean;
  isFetchingMoreExecutions: boolean;

  projectExecutions: { [key: string]: ProductionExecution } | null;
  continuationToken: string | null;

  selectedExecutionGroup: ProductionExecution | null;
  executionGroupLogs: { [key: string]: GetProjectExecutionLogsResult } | null;
}

// Initial State
const moduleState: DeploymentExecutionsPaneState = {
  isBusy: false,
  isFetchingMoreExecutions: false,

  projectExecutions: null,
  continuationToken: null,

  selectedExecutionGroup: null,
  executionGroupLogs: null
};

const DeploymentExecutionsPaneModule: Module<DeploymentExecutionsPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {
    sortedExecutions: state => state.projectExecutions && sortExecutions(Object.values(state.projectExecutions)),
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

          if (!matchingElement) {
            return element;
          }

          // Sets to either green or red
          const executionStatusColorClass =
            matchingElement.type === ExecutionStatusType.EXCEPTION
              ? STYLE_CLASSES.EXECUTION_FAILURE
              : STYLE_CLASSES.EXECUTION_SUCCESS;

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
    [DeploymentExecutionsMutators.setSelectedExecutionGroup](state, group) {
      state.selectedExecutionGroup = group;
    },
    [DeploymentExecutionsMutators.setExecutionGroupLogs](state, logs) {
      state.executionGroupLogs = logs;
    }
  },
  actions: {
    [DeploymentExecutionsActions.resetPane](context) {
      context.commit(DeploymentExecutionsMutators.setIsFetchingMoreExecutions, false);
      context.commit(DeploymentExecutionsMutators.setIsBusy, false);
      context.commit(DeploymentExecutionsMutators.setContinuationToken, null);
      context.commit(DeploymentExecutionsMutators.setProjectExecutions, null);
    },
    async [DeploymentExecutionsActions.getExecutionsForOpenedDeployment](context, withExistingToken?: boolean) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment) {
        console.error('Cannot retrieve logs for deployment: No deployment is opened');
        return;
      }

      // We can set this either for the module or for the sub-pane
      const statusMessageType = withExistingToken
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
