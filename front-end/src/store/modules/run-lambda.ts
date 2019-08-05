import { Module } from 'vuex';
import uuid from 'uuid/v4';
import { RootState } from '../store-types';
import {
  RunLambdaRequest,
  RunLambdaResponse,
  RunLambdaResult,
  RunTmpLambdaEnvironmentVariable,
  RunTmpLambdaRequest,
  RunTmpLambdaResponse
} from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import { LambdaWorkflowState, SupportedLanguage, WorkflowState, WorkflowStateType } from '@/types/graph';
import { RunCodeBlockLambdaConfig, RunTmpCodeBlockLambdaConfig } from '@/types/run-lambda-types';
import { checkBuildStatus, libraryBuildArguments } from '@/store/fetchers/api-helpers';
import { ProductionLambdaWorkflowState } from '@/types/production-workflow-types';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { DeploymentExecutionsActions } from '@/store/modules/panes/deployment-executions-pane';
import { DeploymentViewGetters } from '@/constants/store-constants';

export interface InputDataCache {
  [key: string]: string;
}

// Enums
export enum RunLambdaMutators {
  resetState = 'resetState',
  setLambdaRunningStatus = 'setLambdaRunningStatus',

  setDeployedLambdaRunResult = 'setDeployedLambdaRunResult',
  setDeployedLambdaInputDataCacheEntry = 'setDeployedLambdaInputDataCacheEntry',

  setDevLambdaRunResult = 'setDevLambdaRunResult',
  setDevLambdaRunResultId = 'setDevLambdaRunResultId',
  setDevLambdaInputDataCacheEntry = 'setDevLambdaInputDataCacheEntry',
  setLoadingText = 'setLoadingText'
}

export enum RunLambdaActions {
  runSelectedDeployedCodeBlock = 'runSelectedDeployedCodeBlock',
  makeDeployedLambdaRequest = 'makeDeployedLambdaRequest',

  runSpecifiedEditorCodeBlock = 'runSpecifiedEditorCodeBlock',
  makeDevLambdaRequest = 'makeDevLambdaRequest',
  runLambdaCode = 'runLambdaCode',
  changeDeployedLambdaInputData = 'changeDeployedLambdaInputData',
  changeDevLambdaInputData = 'changeDevLambdaInputData'
}

// Types
export interface RunLambdaState {
  isRunningLambda: boolean;

  deployedLambdaResult: RunLambdaResult | null;
  deployedLambdaInputDataCache: InputDataCache;

  devLambdaResult: RunLambdaResult | null;
  // ID of the last lambda run
  devLambdaResultId: string | null;
  devLambdaInputDataCache: InputDataCache;

  // Text to display while Lambda is being run
  loadingText: string;
}

// Initial State
const moduleState: RunLambdaState = {
  isRunningLambda: false,

  deployedLambdaResult: null,
  deployedLambdaInputDataCache: {},

  devLambdaResult: null,
  /**
   * Used to "identify" run results and associate them against the selected block.
   */
  devLambdaResultId: null,
  devLambdaInputDataCache: {},

  loadingText: 'Running Code Block...'
};

const RunLambdaModule: Module<RunLambdaState, RootState> = {
  namespaced: true,
  state: deepJSONCopy(moduleState),
  getters: {
    /**
     * Absolutely disgusting that this exists here... Because it doesn't use state from this module!
     * But the logic _is_ associated with RunLambda so I'm going to leave this here for now.
     * This feels like the least dirty thing.
     * @param state Vuex state for RunLambdaModule
     * @param getters All getters in RunLambdaModule
     * @param rootState Vuex state for the entire application
     */
    getRunLambdaConfig: (state, getters, rootState) => {
      const projectState = rootState.project;
      // This will never happen...
      if (!projectState.editBlockPane) {
        return null;
      }

      const editBlockPaneState = projectState.editBlockPane;
      const hasValidSelectedNode =
        editBlockPaneState.selectedNode && editBlockPaneState.selectedNode.type === WorkflowStateType.LAMBDA;

      if (!hasValidSelectedNode || !projectState.openedProjectConfig) {
        return null;
      }

      return {
        codeBlock: editBlockPaneState.selectedNode as LambdaWorkflowState,
        projectConfig: projectState.openedProjectConfig
      };
    },
    getDeployedLambdaInputData: (state, getters, rootState) => (id: string) => {
      if (state.deployedLambdaInputDataCache[id]) {
        return state.deployedLambdaInputDataCache[id];
      }

      const viewBlockState = rootState.viewBlock;

      if (viewBlockState.selectedNode && viewBlockState.selectedNode.type === WorkflowStateType.LAMBDA) {
        const lambdaBlock = viewBlockState.selectedNode as LambdaWorkflowState;
        if (lambdaBlock.saved_input_data !== undefined) {
          return lambdaBlock.saved_input_data;
        }
      }

      return '';
    },
    getDevLambdaInputData: (state, getters, rootState) => (id: string) => {
      if (state.devLambdaInputDataCache[id]) {
        return state.devLambdaInputDataCache[id];
      }

      const projectState = rootState.project;
      // This will never happen...
      if (!projectState.editBlockPane) {
        return null;
      }

      const editBlockPaneState = projectState.editBlockPane;
      if (editBlockPaneState.selectedNode && editBlockPaneState.selectedNode.type === WorkflowStateType.LAMBDA) {
        const lambdaBlock = editBlockPaneState.selectedNode as LambdaWorkflowState;
        if (lambdaBlock.saved_input_data !== undefined) {
          return lambdaBlock.saved_input_data;
        }
      }

      return '';
    }
  },
  mutations: {
    [RunLambdaMutators.resetState](state) {
      resetStoreState(state, moduleState);
    },
    [RunLambdaMutators.setLambdaRunningStatus](state, val) {
      state.isRunningLambda = val;
    },
    [RunLambdaMutators.setDeployedLambdaRunResult](state, response) {
      state.deployedLambdaResult = response;
    },
    [RunLambdaMutators.setDeployedLambdaInputDataCacheEntry](state, [id, value]: [string, string]) {
      state.deployedLambdaInputDataCache = {
        ...state.deployedLambdaInputDataCache,
        [id]: value
      };
    },

    [RunLambdaMutators.setDevLambdaRunResult](state, response) {
      state.devLambdaResult = response;
    },
    [RunLambdaMutators.setDevLambdaRunResultId](state, id) {
      state.devLambdaResultId = id;
    },
    [RunLambdaMutators.setDevLambdaInputDataCacheEntry](state, [id, value]: [string, string]) {
      state.devLambdaInputDataCache = {
        ...state.devLambdaInputDataCache,
        [id]: value
      };
    },
    [RunLambdaMutators.setLoadingText](state, loadingText: string) {
      state.loadingText = loadingText;
    }
  },
  actions: {
    async [RunLambdaActions.runSelectedDeployedCodeBlock](context, block: ProductionLambdaWorkflowState) {
      // Grab a default selection if none was specified
      if (!block) {
        const selectedBlock = context.rootGetters[
          `deployment/${DeploymentViewGetters.getSelectedBlock}`
        ] as WorkflowState | null;
        if (!selectedBlock || selectedBlock.type !== WorkflowStateType.LAMBDA) {
          return;
        }

        block = selectedBlock as ProductionLambdaWorkflowState;
      }

      if (!block || !block.arn) {
        console.error('Invalid ARN specified for Run Code Block request');
        return;
      }

      const inputData = context.state.deployedLambdaInputDataCache[block.id] || block.saved_input_data;

      const request: RunLambdaRequest = {
        input_data: inputData === undefined || inputData === null ? '' : inputData,
        arn: block.arn,
        execution_id: uuid()
      };

      await context.dispatch(RunLambdaActions.makeDeployedLambdaRequest, request);
    },
    async [RunLambdaActions.makeDeployedLambdaRequest](context, request: RunLambdaRequest) {
      // Should not ever happen because of types...
      if (!request.arn) {
        console.error('Attempted to run invalid code, no ARN specified');
        return;
      }
      context.commit(RunLambdaMutators.setLambdaRunningStatus, true);

      const runLambdaResult = await makeApiRequest<RunLambdaRequest, RunLambdaResponse>(
        API_ENDPOINT.RunLambda,
        request
      );

      if (!runLambdaResult || !runLambdaResult.success || !runLambdaResult.result) {
        context.commit(RunLambdaMutators.setLambdaRunningStatus, false);
        console.error('Unable to run code, server responded with failure');
        return;
      }

      context.commit(RunLambdaMutators.setDeployedLambdaRunResult, runLambdaResult.result);

      context.commit(RunLambdaMutators.setLambdaRunningStatus, false);

      if (request.execution_id) {
        await context.dispatch(
          `deploymentExecutions/${DeploymentExecutionsActions.forceSelectExecutionGroup}`,
          request.execution_id,
          { root: true }
        );
      }
    },
    async [RunLambdaActions.runSpecifiedEditorCodeBlock](context, config: RunTmpCodeBlockLambdaConfig) {
      if (!config || !config.codeBlock || !config.projectConfig) {
        console.error('Invalid block config specified to execute');
        return;
      }

      const block = config.codeBlock;

      const runLambdaEnvironmentVariables = Object.keys(block.environment_variables).reduce(
        (envVarsOut, id) => {
          const configVariable = config.projectConfig.environment_variables[id];

          // Missing value... Just keep going.
          if (!configVariable) {
            return envVarsOut;
          }

          envVarsOut.push({
            key: block.environment_variables[id].name,
            value: configVariable.value
          });

          return envVarsOut;
        },
        [] as RunTmpLambdaEnvironmentVariable[]
      );

      const inputData = context.state.devLambdaInputDataCache[block.id] || config.codeBlock.saved_input_data;

      const request: RunTmpLambdaRequest = {
        environment_variables: runLambdaEnvironmentVariables,
        input_data: inputData === undefined || inputData === null ? '' : inputData,

        code: block.code,
        language: block.language,
        layers: block.layers,
        libraries: block.libraries,
        max_execution_time: block.max_execution_time,
        memory: block.memory,
        block_id: block.id
      };

      await context.dispatch(RunLambdaActions.makeDevLambdaRequest, request);
    },
    async [RunLambdaActions.makeDevLambdaRequest](context, request: RunTmpLambdaRequest) {
      context.commit(RunLambdaMutators.setLambdaRunningStatus, true);

      const runTmpLambdaResult = await makeApiRequest<RunTmpLambdaRequest, RunTmpLambdaResponse>(
        API_ENDPOINT.RunTmpLambda,
        request
      );
      context.commit(RunLambdaMutators.setLambdaRunningStatus, false);

      const baseError: RunLambdaResult = {
        arn: request.block_id,
        returned_data: 'Unknown run error',
        logs: '',
        truncated: false,
        is_error: true,
        status_code: 500,
        version: 'unknown'
      };

      if (!runTmpLambdaResult) {
        context.commit(RunLambdaMutators.setDevLambdaRunResult, baseError);
        context.commit(RunLambdaMutators.setDevLambdaRunResultId, request.block_id);
        console.error('Unable to run code, server responded with unknown failure');
        return;
      }

      if (
        !runTmpLambdaResult.success &&
        runTmpLambdaResult.msg !== undefined &&
        runTmpLambdaResult.log_output !== undefined
      ) {
        baseError.returned_data = `Error Running Block: ${runTmpLambdaResult.msg}`;
        baseError.logs = runTmpLambdaResult.log_output;

        context.commit(RunLambdaMutators.setDevLambdaRunResult, baseError);
        context.commit(RunLambdaMutators.setDevLambdaRunResultId, request.block_id);
        console.error('Unable to run code, server responded with failure', runTmpLambdaResult);
        return;
      }

      if (!runTmpLambdaResult.result) {
        baseError.returned_data = 'Unknown run error, missing result';

        context.commit(RunLambdaMutators.setDevLambdaRunResult, baseError);
        context.commit(RunLambdaMutators.setDevLambdaRunResultId, request.block_id);
        console.error('Unable to run code, server responded with missing result');
        return;
      }

      context.commit(RunLambdaMutators.setDevLambdaRunResult, runTmpLambdaResult.result);
      context.commit(RunLambdaMutators.setDevLambdaRunResultId, request.block_id);
    },
    async [RunLambdaActions.runLambdaCode](context, config?: RunCodeBlockLambdaConfig) {
      if (context.rootState.project.isInDemoMode) {
        await context.dispatch(`unauthViewProject/promptDemoModeSignup`, true, { root: true });
        return;
      }

      function getLoadingText(isBuildCached: boolean) {
        if (isBuildCached) {
          return 'Running Code Block...';
        }
        return 'Building libraries and then running Code Block...\n(Note: The first run after adding a new library may take up to two minutes longer to finish.)';
      }

      // Try to get the default config
      if (!config) {
        config = context.getters.getRunLambdaConfig as RunCodeBlockLambdaConfig;
      }

      // Means we don't have a default config either...
      if (!config) {
        return;
      }

      context.commit(RunLambdaMutators.setDevLambdaRunResult, null);
      context.commit(RunLambdaMutators.setLambdaRunningStatus, true);

      const params: libraryBuildArguments = {
        language: config.codeBlock.language as SupportedLanguage,
        libraries: config.codeBlock.libraries
      };
      const isLibraryBuildCached = await checkBuildStatus(params);
      context.commit(RunLambdaMutators.setLoadingText, getLoadingText(isLibraryBuildCached));

      await context.dispatch(RunLambdaActions.runSpecifiedEditorCodeBlock, config);
    },
    async [RunLambdaActions.changeDevLambdaInputData](context, [id, inputData]: [string, string]) {
      context.commit(RunLambdaMutators.setDevLambdaInputDataCacheEntry, [id, inputData]);
    },
    async [RunLambdaActions.changeDeployedLambdaInputData](context, [id, inputData]: [string, string]) {
      context.commit(RunLambdaMutators.setDeployedLambdaInputDataCacheEntry, [id, inputData]);
    }
  }
};

export default RunLambdaModule;
