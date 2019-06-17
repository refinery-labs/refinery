import {Module} from 'vuex';
import {RootState} from '../../store-types';
import {Execution} from '@/types/api-types';
import {getProjectExecutions} from '@/store/fetchers/api-helpers';

// Enums
export enum DeploymentExecutionsMutators {
  setIsBusy = 'setIsBusy',
  setProjectExecutions = 'setProjectExecutions'
}

export enum DeploymentExecutionsActions {
  getExecutionsForOpenedDeployment = 'getExecutionsForOpenedDeployment'
}

// Types
export interface DeploymentExecutionsPaneState {
  isBusy: boolean,

  projectExecutions: { [key: string]: Execution } | null
}

// Initial State
const moduleState: DeploymentExecutionsPaneState = {
  isBusy: false,

  projectExecutions: null
};

const DeploymentExecutionsPaneModule: Module<DeploymentExecutionsPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [DeploymentExecutionsMutators.setIsBusy](state, busy) {
      state.isBusy = busy;
    },
    [DeploymentExecutionsMutators.setProjectExecutions](state, executions) {
      state.projectExecutions = executions;
    }
  },
  actions: {

    async [DeploymentExecutionsActions.getExecutionsForOpenedDeployment](context) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment) {
        console.error('Cannot retrieve logs for deployment: No deployment is opened');
        return;
      }

      context.commit(DeploymentExecutionsMutators.setIsBusy, true);

      // This is used by the async data fetching flow
      let hasIncrementallyAddedResults = false;

      // This is kind of a gross way to make the UI more responsive... But it feels reasonable for now.
      // TODO: Gut out the "non-async" flow code to decrease the complexity of this? Maybe use an EventEmitter?
      const executionsResponse = await getProjectExecutions(deploymentStore.openedDeployment.project_id, (result) => {
        hasIncrementallyAddedResults = true;

        // We have the first result of many, so set busy to false while we stuff data into the UI
        context.commit(DeploymentExecutionsMutators.setIsBusy, false);

        context.commit(DeploymentExecutionsMutators.setProjectExecutions, {
          ...(context.state.projectExecutions || {}),
          ...result
        });
      });

      if (!executionsResponse) {
        console.error('Unable to fetch execution logs, did not receive any results from server');
        context.commit(DeploymentExecutionsMutators.setIsBusy, false);
        return;
      }

      // We async retrieved this data already, so no need to continue.
      if (hasIncrementallyAddedResults) {
        return;
      }

      context.commit(DeploymentExecutionsMutators.setProjectExecutions, executionsResponse);
      context.commit(DeploymentExecutionsMutators.setIsBusy, false);
    }
  }
};

export default DeploymentExecutionsPaneModule;
