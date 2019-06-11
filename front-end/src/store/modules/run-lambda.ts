import {Module} from 'vuex';
import {RootState} from '../store-types';
import {RunLambdaRequest, RunLambdaResponse} from '@/types/api-types';
import {makeApiRequest} from '@/store/fetchers/refinery-api';
import {API_ENDPOINT} from '@/constants/api-constants';

// Enums
export enum RunLambdaMutators {}

export enum RunLambdaActions {
  runDeployedLambda = 'runLambda'
}

// Types
export interface RunLambdaState {}

// Initial State
const moduleState: RunLambdaState = {};

const RunLambdaModule: Module<RunLambdaState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {},
  actions: {
    async [RunLambdaActions.runDeployedLambda](context, request: RunLambdaRequest) {
      if (!request.arn) {
        console.error('Attempted to run invalid code, no ARN specified');
        return;
      }

      const runLambdaResult = await makeApiRequest<RunLambdaRequest, RunLambdaResponse>(API_ENDPOINT.RunLambda, request);

      if (!runLambdaResult || !runLambdaResult.success || !runLambdaResult.result) {
        console.error('Unable to run code, server responded with failure');
        return;
      }

      runLambdaResult.result
    }
  }
};

export default RunLambdaModule;
