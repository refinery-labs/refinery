import {Module} from 'vuex';
import {RootState} from '../store-types';
import {
  RunLambdaRequest,
  RunLambdaResponse,
  RunLambdaResult,
  RunTmpLambdaRequest,
  RunTmpLambdaResponse
} from '@/types/api-types';
import {makeApiRequest} from '@/store/fetchers/refinery-api';
import {API_ENDPOINT} from '@/constants/api-constants';
import {LambdaWorkflowState, ProjectConfig, WorkflowState, WorkflowStateType} from '@/types/graph';
import {RunCodeBlockLambdaConfig} from '@/types/run-lambda-types';

// Enums
export enum RunLambdaMutators {
  setLambdaRunningStatus = 'setLambdaRunningStatus',

  setDeployedLambdaRunResult = 'setDeployedLambdaRunResult',
  setDeployedLambdaInputData = 'setDeployedLambdaInputData',

  setDevLambdaRunResult = 'setDevLambdaRunResult',
  setDevLambdaInputData = 'setDevLambdaInputData'

}

export enum RunLambdaActions {
  runSelectedDeployedCodeBlock = 'runSelectedDeployedCodeBlock',
  makeDeployedLambdaRequest = 'makeDeployedLambdaRequest',

  runSpecifiedEditorCodeBlock = 'runSpecifiedEditorCodeBlock',
  makeDevLambdaRequest = 'makeDevLambdaRequest'
}

// Types
export interface RunLambdaState {
  isRunningLambda: boolean,

  deployedLambdaResult: RunLambdaResult | null,
  deployedLambdaInputData: string,

  devLambdaResult: RunLambdaResult | null,
  devLambdaInputData: string
}

// Initial State
const moduleState: RunLambdaState = {
  isRunningLambda: false,

  deployedLambdaResult: null,
  deployedLambdaInputData: '',

  devLambdaResult: null,
  devLambdaInputData: ''
};

const RunLambdaModule: Module<RunLambdaState, RootState> = {
  namespaced: true,
  state: moduleState,
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
      const hasValidSelectedNode
        = editBlockPaneState.selectedNode && editBlockPaneState.selectedNode.type === WorkflowStateType.LAMBDA;

      if (!hasValidSelectedNode || !projectState.openedProjectConfig) {
        return null;
      }

      return {
        codeBlock: editBlockPaneState.selectedNode as LambdaWorkflowState,
        projectConfig: projectState.openedProjectConfig
      };
    }
  },
  mutations: {
    [RunLambdaMutators.setLambdaRunningStatus](state, val) {
      state.isRunningLambda = val;
    },
    [RunLambdaMutators.setDeployedLambdaRunResult](state, response) {
      state.deployedLambdaResult = response;
    },
    [RunLambdaMutators.setDeployedLambdaInputData](state, inputData) {
      state.deployedLambdaInputData = inputData;
    },

    [RunLambdaMutators.setDevLambdaRunResult](state, response) {
      state.devLambdaResult = response;
    },
    [RunLambdaMutators.setDevLambdaInputData](state, inputData) {
      state.devLambdaInputData = inputData;
    }
  },
  actions: {
    async [RunLambdaActions.runSelectedDeployedCodeBlock](context) {
      // Get selected node from Deployment UI
      // Create request object and fire off `makeDeployedLambdaRequest`
    },
    async [RunLambdaActions.makeDeployedLambdaRequest](context, request: RunLambdaRequest) {

      // Should not ever happen because of types...
      if (!request.arn || !request.input_data) {
        console.error('Attempted to run invalid code, no ARN specified');
        return;
      }
      context.commit(RunLambdaMutators.setLambdaRunningStatus, true);

      const runLambdaResult = await makeApiRequest<RunLambdaRequest, RunLambdaResponse>(API_ENDPOINT.RunLambda, request);

      if (!runLambdaResult || !runLambdaResult.success || !runLambdaResult.result) {
        context.commit(RunLambdaMutators.setLambdaRunningStatus, false);
        console.error('Unable to run code, server responded with failure');
        return;
      }

      context.commit(RunLambdaMutators.setLambdaRunningStatus, false);
      context.commit(RunLambdaMutators.setDeployedLambdaRunResult, runLambdaResult.result);
    },

    async [RunLambdaActions.runSpecifiedEditorCodeBlock](context, config: RunCodeBlockLambdaConfig) {
      if (!config || !config.codeBlock || !config.projectConfig) {
        console.error('Invalid block config specified to execute');
        return;
      }

      const block = config.codeBlock;

      const request: RunTmpLambdaRequest = {
        environment_variables: config.projectConfig.environment_variables[config.codeBlock.id] || [],
        input_data: context.state.devLambdaInputData,

        code: block.code,
        language: block.language,
        layers: block.layers,
        libraries: block.libraries,
        max_execution_time: block.max_execution_time,
        memory: block.memory
      };

      await context.dispatch(RunLambdaActions.makeDevLambdaRequest, request);
    },
    async [RunLambdaActions.makeDevLambdaRequest](context, request: RunTmpLambdaRequest) {
      context.commit(RunLambdaMutators.setLambdaRunningStatus, true);

      const runTmpLambdaResult = await makeApiRequest<RunTmpLambdaRequest, RunTmpLambdaResponse>(API_ENDPOINT.RunTmpLambda, request);

      if (!runTmpLambdaResult || !runTmpLambdaResult.success || !runTmpLambdaResult.result) {
        context.commit(RunLambdaMutators.setLambdaRunningStatus, false);
        console.error('Unable to run code, server responded with failure');
        return;
      }

      context.commit(RunLambdaMutators.setLambdaRunningStatus, false);
      context.commit(RunLambdaMutators.setDevLambdaRunResult, runTmpLambdaResult.result);
    }
  }
};

export default RunLambdaModule;
