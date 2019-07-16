import { Module } from 'vuex';
import uuid from 'uuid/v4';
import { RootState } from '../../store-types';
import {
  getAdditionalLogsByPage,
  getContentsForLogs,
  getLogsForExecutions,
  getProjectExecutions
} from '@/store/fetchers/api-helpers';
import {
  AdditionalBlockExecutionPage,
  BlockExecutionGroup,
  BlockExecutionLog,
  BlockExecutionLogContentsByLogId,
  BlockExecutionLogsForBlockId,
  BlockExecutionPagesByBlockId,
  BlockExecutionTotalsByBlockId,
  ProjectExecution,
  ProjectExecutionsByExecutionId
} from '@/types/deployment-executions-types';
import { sortExecutions } from '@/utils/project-execution-utils';
import { STYLE_CLASSES } from '@/lib/cytoscape-styles';
import { deepJSONCopy } from '@/lib/general-utils';
import { autoRefreshJob, waitUntil } from '@/utils/async-utils';
import { SIDEBAR_PANE } from '@/types/project-editor-types';
import { DeploymentViewActions } from '@/constants/store-constants';
import { ExecutionLogMetadata, ExecutionStatusType } from '@/types/execution-logs-types';

// Enums
export enum DeploymentExecutionsGetters {
  sortedExecutions = 'sortedExecutions',
  getSelectedProjectExecution = 'getSelectedProjectExecution',
  getBlockExecutionGroupForSelectedBlock = 'getBlockExecutionGroupForSelectedBlock',
  doesSelectedBlockHaveExecutions = 'doesSelectedBlockHaveExecutions',
  currentlySelectedLogId = 'currentlySelectedLogId',
  getAllLogIdsForSelectedBlock = 'getAllLogIdsForSelectedBlock',
  getAllLogMetadataForSelectedBlock = 'getAllLogMetadataForSelectedBlock',
  getLogForSelectedBlock = 'getLogForSelectedBlock',
  getBlockExecutionTotalsForSelectedBlock = 'getBlockExecutionTotalsForSelectedBlock',
  graphElementsWithExecutionStatus = 'graphElementsWithExecutionStatus'
}

export enum DeploymentExecutionsMutators {
  resetPane = 'resetPane',
  setIsBusy = 'setIsBusy',
  setIsFetchingMoreExecutions = 'setIsFetchingMoreExecutions',
  setIsFetchingLogs = 'setIsFetchingLogs',
  setIsFetchingMoreLogs = 'setIsFetchingMoreLogs',
  setProjectExecutions = 'setProjectExecutions',
  setNextTimestampToRetreive = 'setNextTimestampToRetreive',

  setAutoRefreshJobRunning = 'setAutoRefreshJobRunning',
  setAutoRefreshJobIterations = 'setAutoRefreshJobIterations',
  setAutoRefreshJobNonce = 'setAutoRefreshJobNonce',

  setSelectedExecutionGroup = 'setSelectedExecutionGroup',
  resetLogState = 'resetLogState',
  addBlockExecutionLogMetadata = 'addBlockExecutionLogMetadata',
  addBlockExecutionPageResult = 'addBlockExecutionPageResult',
  addBlockExecutionLogContents = 'addBlockExecutionLogContents',
  setSelectedBlockExecutionLog = 'setSelectedBlockExecutionLog'
}

export enum DeploymentExecutionsActions {
  activatePane = 'activatePane',
  getExecutionsForOpenedDeployment = 'getExecutionsForOpenedDeployment',
  openExecutionGroup = 'openExecutionGroup',
  fetchLogsForSelectedBlock = 'fetchLogsForSelectedBlock',
  selectLogByLogId = 'selectLogByLogId',
  fetchLogsByIds = 'fetchLogsByIds',
  warmLogCacheAndSelectDefault = 'warmLogCacheAndSelectDefault',
  fetchMoreLogsForSelectedBlock = 'fetchMoreLogsForSelectedBlock'
}

// Types
export interface DeploymentExecutionsPaneState {
  isBusy: boolean;
  isFetchingMoreExecutions: boolean;
  isFetchingLogs: boolean;
  isFetchingMoreLogs: boolean;

  projectExecutions: ProjectExecutionsByExecutionId | null;
  selectedProjectExecution: string | null;

  blockExecutionLogByLogId: BlockExecutionLogContentsByLogId;
  blockExecutionLogsForBlockId: BlockExecutionLogsForBlockId;
  blockExecutionTotalsByBlockId: BlockExecutionTotalsByBlockId;
  blockExecutionPagesByBlockId: BlockExecutionPagesByBlockId;

  selectedBlockExecutionLog: string | null;

  nextTimestampToRetreive: number | null;
  autoRefreshJobRunning: boolean;
  autoRefreshJobIterations: number;
  autoRefreshJobNonce: string | null;
}

// Initial State
const moduleState: DeploymentExecutionsPaneState = {
  isBusy: false,
  isFetchingMoreExecutions: false,
  isFetchingLogs: false,
  isFetchingMoreLogs: false,

  projectExecutions: null,
  selectedProjectExecution: null,

  blockExecutionLogByLogId: {},
  blockExecutionLogsForBlockId: {},
  blockExecutionTotalsByBlockId: {},
  blockExecutionPagesByBlockId: {},

  selectedBlockExecutionLog: null,

  nextTimestampToRetreive: null,
  autoRefreshJobRunning: false,
  autoRefreshJobIterations: 0,
  autoRefreshJobNonce: null
};

function getExecutionStatusStyleForLogs(logs: BlockExecutionGroup) {
  if (logs.executionStatus === ExecutionStatusType.EXCEPTION) {
    return STYLE_CLASSES.EXECUTION_FAILURE;
  }

  if (logs.executionStatus === ExecutionStatusType.CAUGHT_EXCEPTION) {
    return STYLE_CLASSES.EXECUTION_CAUGHT;
  }

  return STYLE_CLASSES.EXECUTION_SUCCESS;
}

const DeploymentExecutionsPaneModule: Module<DeploymentExecutionsPaneState, RootState> = {
  namespaced: true,
  state: deepJSONCopy(moduleState),
  getters: {
    [DeploymentExecutionsGetters.sortedExecutions]: state =>
      state.projectExecutions && sortExecutions(Object.values(state.projectExecutions)),

    [DeploymentExecutionsGetters.getSelectedProjectExecution]: state =>
      state.selectedProjectExecution &&
      state.projectExecutions &&
      state.projectExecutions[state.selectedProjectExecution],

    [DeploymentExecutionsGetters.getBlockExecutionGroupForSelectedBlock]: (state, getters, rootState) => {
      const selectedProjectExecution: ProjectExecution | null =
        getters[DeploymentExecutionsGetters.getSelectedProjectExecution];

      if (!rootState.viewBlock.selectedNode || !selectedProjectExecution) {
        return null;
      }

      return selectedProjectExecution.blockExecutionGroupByBlockId[rootState.viewBlock.selectedNode.id];
    },
    [DeploymentExecutionsGetters.doesSelectedBlockHaveExecutions]: (state, getters) => {
      const blockExecutions: BlockExecutionGroup | null =
        getters[DeploymentExecutionsGetters.getBlockExecutionGroupForSelectedBlock];

      if (!blockExecutions) {
        return false;
      }

      return blockExecutions.totalExecutionCount > 0;
    },
    [DeploymentExecutionsGetters.currentlySelectedLogId]: (state, getters) => {
      const blockLogIds: string[] | null = getters[DeploymentExecutionsGetters.getAllLogIdsForSelectedBlock];

      // We don't have logs for the selected block
      if (!blockLogIds) {
        return null;
      }

      // We have an invalid selection, so return the first log available.
      if (state.selectedBlockExecutionLog === null || !blockLogIds.includes(state.selectedBlockExecutionLog)) {
        // Return a default selection, if we have default logs available for the selected block
        return blockLogIds[0] ? blockLogIds[0] : null;
      }

      // Return the selected log because it matches the currently selected block's logs :)
      return state.selectedBlockExecutionLog;
    },
    [DeploymentExecutionsGetters.getAllLogIdsForSelectedBlock]: (state, getters) => {
      const allLogMetadata: ExecutionLogMetadata[] | null =
        getters[DeploymentExecutionsGetters.getAllLogMetadataForSelectedBlock];

      return allLogMetadata ? allLogMetadata.map(log => log.log_id) : null;
    },
    [DeploymentExecutionsGetters.getAllLogMetadataForSelectedBlock]: (state, getters, rootState) => {
      if (!rootState.viewBlock.selectedNode) {
        return null;
      }

      const selectedBlockLogs = state.blockExecutionLogsForBlockId[rootState.viewBlock.selectedNode.id];

      if (!selectedBlockLogs) {
        return null;
      }

      return selectedBlockLogs;
    },
    [DeploymentExecutionsGetters.getLogForSelectedBlock]: (state, getters) => {
      const currentlySelectedLogId: string | null = getters[DeploymentExecutionsGetters.currentlySelectedLogId];

      // We don't have any logs to render for the current block
      if (currentlySelectedLogId === null) {
        return null;
      }

      return state.blockExecutionLogByLogId[currentlySelectedLogId];
    },
    [DeploymentExecutionsGetters.getBlockExecutionTotalsForSelectedBlock]: (state, getters, rootState) => {
      if (!rootState.viewBlock.selectedNode) {
        return null;
      }

      return state.blockExecutionTotalsByBlockId[rootState.viewBlock.selectedNode.id];
    },
    [DeploymentExecutionsGetters.graphElementsWithExecutionStatus]: (state, getters, rootState) => {
      if (
        !rootState.deployment.cytoscapeElements ||
        !state.projectExecutions ||
        state.selectedProjectExecution === null
      ) {
        return null;
      }

      const executionGroup = state.projectExecutions[state.selectedProjectExecution];

      const elements = rootState.deployment.cytoscapeElements;

      // Go through the graph and set each style to be of a color based on execution status
      const nodes =
        elements.nodes &&
        elements.nodes.map(element => {
          if (element.data.id === undefined) {
            return element;
          }

          const matchingElement = executionGroup.blockExecutionGroupByBlockId[element.data.id];

          if (!matchingElement) {
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
      Object.keys(moduleState).forEach(key => (state[key] = deepJSONCopy(moduleState[key])));
    },
    [DeploymentExecutionsMutators.setIsBusy](state, busy) {
      state.isBusy = busy;
    },
    [DeploymentExecutionsMutators.setIsFetchingMoreExecutions](state, isFetching) {
      state.isFetchingMoreExecutions = isFetching;
    },
    [DeploymentExecutionsMutators.setIsFetchingLogs](state, isFetching) {
      state.isFetchingLogs = isFetching;
    },
    [DeploymentExecutionsMutators.setIsFetchingMoreLogs](state, isFetching) {
      state.isFetchingMoreLogs = isFetching;
    },
    [DeploymentExecutionsMutators.setNextTimestampToRetreive](state, timestamp) {
      state.nextTimestampToRetreive = timestamp;
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

    [DeploymentExecutionsMutators.setProjectExecutions](state, executions) {
      state.projectExecutions = executions;
    },
    [DeploymentExecutionsMutators.setSelectedExecutionGroup](state, group) {
      state.selectedProjectExecution = group;
    },
    [DeploymentExecutionsMutators.resetLogState](state) {
      // We must reset the state between changing selected executions...
      // TODO: Keep state around via ExecutionId instead of BlockId to allow "caching"? But that might explode memory usage too?
      // blockExecutionLogByLogId: BlockExecutionLogContentsByLogId;
      state.blockExecutionLogsForBlockId = deepJSONCopy(moduleState.blockExecutionLogsForBlockId);
      state.blockExecutionTotalsByBlockId = deepJSONCopy(moduleState.blockExecutionTotalsByBlockId);
      state.blockExecutionPagesByBlockId = deepJSONCopy(moduleState.blockExecutionPagesByBlockId);
    },
    [DeploymentExecutionsMutators.addBlockExecutionLogMetadata](state, log: BlockExecutionLog) {
      state.blockExecutionLogsForBlockId = {
        ...state.blockExecutionLogsForBlockId,
        [log.blockId]: [...(state.blockExecutionLogsForBlockId[log.blockId] || []), ...Object.values(log.logs)]
      };

      state.blockExecutionPagesByBlockId = {
        ...state.blockExecutionPagesByBlockId,
        ...{ [log.blockId]: log.pages }
      };

      state.blockExecutionTotalsByBlockId = {
        ...state.blockExecutionTotalsByBlockId,
        [log.blockId]: log.totalExecutions
      };
    },
    [DeploymentExecutionsMutators.addBlockExecutionPageResult](state, log: AdditionalBlockExecutionPage) {
      state.blockExecutionLogsForBlockId = {
        ...state.blockExecutionLogsForBlockId,
        [log.blockId]: [...(state.blockExecutionLogsForBlockId[log.blockId] || []), ...Object.values(log.logs)]
      };

      state.blockExecutionPagesByBlockId = {
        ...state.blockExecutionPagesByBlockId,
        // Remove the page we just retrieved
        [log.blockId]: state.blockExecutionPagesByBlockId[log.blockId].filter(page => page !== log.page)
      };
    },
    [DeploymentExecutionsMutators.addBlockExecutionLogContents](state, logs: BlockExecutionLogContentsByLogId) {
      state.blockExecutionLogByLogId = {
        ...state.blockExecutionLogByLogId,
        ...logs
      };
    },
    [DeploymentExecutionsMutators.setSelectedBlockExecutionLog](state, index) {
      state.selectedBlockExecutionLog = index;
    }
  },
  actions: {
    async [DeploymentExecutionsActions.activatePane](context) {
      // TODO: Set a different busy symbol when refreshing
      await context.dispatch(DeploymentExecutionsActions.getExecutionsForOpenedDeployment);

      const nonce = uuid();

      // Setting this will tell the previous job that it's no longer in control.
      context.commit(DeploymentExecutionsMutators.setAutoRefreshJobNonce, nonce);

      // Wait for the old job to die
      if (context.state.autoRefreshJobRunning) {
        // Wait for the previous job to finish
        await waitUntil(3000, 10, () => context.state.autoRefreshJobRunning);
      }

      context.commit(DeploymentExecutionsMutators.setAutoRefreshJobRunning, true);

      await autoRefreshJob({
        timeoutMs: 5000,
        maxIterations: 125, // 5 minutes
        nonce: nonce,
        makeRequest: async () => {
          await context.dispatch(DeploymentExecutionsActions.getExecutionsForOpenedDeployment, false);
        },
        isStillValid: async (nonce, iteration) => {
          const valid = nonce === context.state.autoRefreshJobNonce;

          // If another job is running, kill this one.
          if (!valid) {
            return false;
          }

          // Only commit if we are still wanted
          context.commit(DeploymentExecutionsMutators.setAutoRefreshJobIterations, iteration);
          return true;
        },
        onComplete: async () => {
          context.commit(DeploymentExecutionsMutators.setAutoRefreshJobRunning, false);
        }
      });
    },
    async [DeploymentExecutionsActions.getExecutionsForOpenedDeployment](context, withExistingToken?: boolean) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment) {
        console.error('Cannot retrieve logs for deployment: No deployment is opened');
        return;
      }

      // TODO: Do we need to check if an existing network request is already in-flight?
      // We can set this either for the module or for the sub-pane
      const statusMessageType =
        context.state.projectExecutions !== null
          ? DeploymentExecutionsMutators.setIsFetchingMoreExecutions
          : DeploymentExecutionsMutators.setIsBusy;

      context.commit(statusMessageType, true);

      // We may either use the last timestamp or not.
      const timestampToContinueWith = withExistingToken ? context.state.nextTimestampToRetreive : null;

      const executionsResponse = await getProjectExecutions(deploymentStore.openedDeployment, timestampToContinueWith);

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
      context.commit(DeploymentExecutionsMutators.setNextTimestampToRetreive, executionsResponse.oldestTimestamp);

      if (context.state.selectedProjectExecution !== null) {
        await context.dispatch(DeploymentExecutionsActions.fetchLogsForSelectedBlock);
      }

      context.commit(statusMessageType, false);
    },
    async [DeploymentExecutionsActions.openExecutionGroup](context, executionId: string) {
      context.commit(DeploymentExecutionsMutators.resetLogState);

      context.commit(DeploymentExecutionsMutators.setSelectedExecutionGroup, executionId);

      context.commit(DeploymentExecutionsMutators.setIsBusy, true);

      const selectedExecution: ProjectExecution =
        context.getters[DeploymentExecutionsGetters.getSelectedProjectExecution];

      const blocks = selectedExecution.blockExecutionGroupByBlockId;
      const blockIds = Object.keys(selectedExecution.blockExecutionGroupByBlockId);

      // Find the block with the earliest timestamp so that we select the "first" execution
      const lowestTimestampBlock = blockIds.reduce((lowestId, id) => {
        // Compare timestamps and if the current block's timestamp is the lowest, use that.
        if (blocks[id].timestamp < blocks[lowestId].timestamp) {
          return id;
        }

        return lowestId;
      }, blockIds[0]);

      await context.dispatch(`deployment/${DeploymentViewActions.selectNode}`, lowestTimestampBlock, { root: true });

      await context.dispatch(DeploymentExecutionsActions.fetchLogsForSelectedBlock);

      // "Convert" the currently opened pane into the execution view pane
      if (
        context.rootState.deployment.activeRightSidebarPane === SIDEBAR_PANE.viewDeployedBlock &&
        context.getters[DeploymentExecutionsGetters.doesSelectedBlockHaveExecutions]
      ) {
        await context.dispatch(
          `deployment/${DeploymentViewActions.openRightSidebarPane}`,
          SIDEBAR_PANE.viewDeployedBlockLogs,
          { root: true }
        );
      }

      // If the currently selected pane no longer has executions, "convert" back to view block pane
      if (
        context.rootState.deployment.activeRightSidebarPane === SIDEBAR_PANE.viewDeployedBlockLogs &&
        !context.getters[DeploymentExecutionsGetters.doesSelectedBlockHaveExecutions]
      ) {
        await context.dispatch(
          `deployment/${DeploymentViewActions.openRightSidebarPane}`,
          SIDEBAR_PANE.viewDeployedBlock,
          { root: true }
        );
      }

      context.commit(DeploymentExecutionsMutators.setIsBusy, false);
    },
    async [DeploymentExecutionsActions.fetchLogsForSelectedBlock](context) {
      const selectedProjectExecution: ProjectExecution =
        context.getters[DeploymentExecutionsGetters.getSelectedProjectExecution];

      if (!selectedProjectExecution || !context.rootState.deployment.openedDeployment) {
        console.error('Attempted to open project execution with invalid selected execution group');
        return;
      }

      const blockExecutionGroupForSelectedBlock: BlockExecutionGroup =
        context.getters[DeploymentExecutionsGetters.getBlockExecutionGroupForSelectedBlock];

      // No logs to fetch for selected block, probably
      if (!blockExecutionGroupForSelectedBlock) {
        return;
      }

      const totalExecutionsForBlock: number | null =
        context.getters[DeploymentExecutionsGetters.getBlockExecutionTotalsForSelectedBlock];

      // If our current "view" of the log execution totals is correct, then don't fetch any more.
      if (
        totalExecutionsForBlock &&
        totalExecutionsForBlock === blockExecutionGroupForSelectedBlock.totalExecutionCount
      ) {
        return;
      }

      context.commit(DeploymentExecutionsMutators.setIsFetchingLogs, true);

      const response = await getLogsForExecutions(
        context.rootState.deployment.openedDeployment,
        blockExecutionGroupForSelectedBlock
      );

      context.commit(DeploymentExecutionsMutators.setIsFetchingLogs, false);

      if (!response) {
        console.error('Unable to retrieve logs for execution');
        return;
      }

      context.commit(DeploymentExecutionsMutators.addBlockExecutionLogMetadata, response);

      await context.dispatch(DeploymentExecutionsActions.warmLogCacheAndSelectDefault, response);
    },
    // TODO: Merge this with the above logic because it's gross af.
    async [DeploymentExecutionsActions.fetchMoreLogsForSelectedBlock](context) {
      const selectedProjectExecution: ProjectExecution =
        context.getters[DeploymentExecutionsGetters.getSelectedProjectExecution];

      if (!selectedProjectExecution) {
        console.error('Attempted to open project execution with invalid selected execution group');
        return;
      }

      const selectedNode = context.rootState.viewBlock.selectedNode;

      if (!selectedNode) {
        return null;
      }

      const pages = context.state.blockExecutionPagesByBlockId[selectedNode.id];

      context.commit(DeploymentExecutionsMutators.setIsFetchingMoreLogs, true);

      if (!pages || pages.length === 0) {
        console.error('No more logs to retrieve');
        return;
      }

      const response = await getAdditionalLogsByPage(selectedNode.id, pages[0]);

      context.commit(DeploymentExecutionsMutators.setIsFetchingMoreLogs, false);

      if (!response) {
        console.error('Unable to retrieve additional logs for execution');
        return;
      }

      context.commit(DeploymentExecutionsMutators.addBlockExecutionPageResult, response);

      await context.dispatch(DeploymentExecutionsActions.warmLogCacheAndSelectDefault, response);
    },
    async [DeploymentExecutionsActions.selectLogByLogId](context, logId: string) {
      // We already have the log, so just set it as selected and move on.
      if (context.state.blockExecutionLogByLogId[logId]) {
        context.commit(DeploymentExecutionsMutators.setSelectedBlockExecutionLog, logId);
        return;
      }

      const selectedNode = context.rootState.viewBlock.selectedNode;

      if (!selectedNode) {
        console.error('Unable to fetch logs, no block selected');
        return;
      }

      const executionLogs = context.state.blockExecutionLogsForBlockId[selectedNode.id];

      if (!executionLogs) {
        console.error('Unable to fetch logs, could not find selected block in executions');
        return;
      }

      const logMetadata = executionLogs.find(execution => execution.log_id === logId);

      if (!logMetadata) {
        console.error('Unable to fetch log, missing log metadata for specified log id');
        return;
      }

      context.commit(DeploymentExecutionsMutators.setIsFetchingMoreLogs, true);

      context.commit(DeploymentExecutionsMutators.setSelectedBlockExecutionLog, logId);

      await context.dispatch(DeploymentExecutionsActions.fetchLogsByIds, [logMetadata]);

      // Setting the end of loading after we set the result.
      context.commit(DeploymentExecutionsMutators.setIsFetchingMoreLogs, false);
    },
    async [DeploymentExecutionsActions.fetchLogsByIds](context, logsToFetch: ExecutionLogMetadata[]) {
      if (!logsToFetch || logsToFetch.length === 0) {
        return;
      }

      const logContents = await getContentsForLogs(logsToFetch);

      if (!logContents) {
        console.error('Unable to fetch log contents, api request did not succeed');
        return;
      }

      context.commit(DeploymentExecutionsMutators.addBlockExecutionLogContents, logContents);
    },
    async [DeploymentExecutionsActions.warmLogCacheAndSelectDefault](
      context,
      logMetadataByLogId: AdditionalBlockExecutionPage | BlockExecutionLog
    ) {
      if (!logMetadataByLogId) {
        return;
      }

      const logIds = Object.keys(logMetadataByLogId.logs);

      if (logIds.length === 0) {
        return;
      }

      const selectedBlock = context.rootState.viewBlock.selectedNode;

      // Select a default, plus make sure we're currently looking at the right block before selecting...
      if (selectedBlock && selectedBlock.id === logMetadataByLogId.blockId) {
        await context.dispatch(DeploymentExecutionsActions.selectLogByLogId, logIds[0]);
      }

      const fourMoreLogs = logIds.slice(1, 5);

      if (fourMoreLogs.length > 0) {
        await context.dispatch(
          DeploymentExecutionsActions.fetchLogsByIds,
          fourMoreLogs.map(id => logMetadataByLogId.logs[id])
        );
      }
    }
  }
};

export default DeploymentExecutionsPaneModule;
