import Vue from 'vue';
import Vuex from 'vuex';
import SettingPlugin from './plugins/setting';
import SettingModule from './modules/setting';
import UserModule from './modules/user';
import createPersistedState from 'vuex-persistedstate';
import ProjectView from './modules/project-view';
import AllProjects from './modules/all-projects';
import { RootState } from '@/store/store-types';
import ToastPaneModule from '@/store/modules/toasts';
import DeploymentViewModule from '@/store/modules/deployment-view';
import BillingPaneModule from '@/store/modules/billing';
import RunLambdaModule from '@/store/modules/run-lambda';
import ViewBlockPaneModule from '@/store/modules/panes/view-block-pane';
import ViewTransitionPaneModule from '@/store/modules/panes/view-transition-pane';
import DeploymentExecutionsPaneModule from '@/store/modules/panes/deployment-executions-pane';
import ActionLoggerPlugin from '@/store/plugins/action-logger';
import ServerStateLoggerPlugin from '@/store/plugins/server-state-logger';

Vue.use(Vuex);

const isDevelopment = process.env.NODE_ENV !== 'production';

const persistedStorePaths = [
  // 'setting',
  // 'project',
  // 'allProjects',
  'user.loginEmailInput',
  'user.rememberMeToggled'
];

const plugins = [
  // TODO: This is busted... Dang
  createPersistedState({
    paths: persistedStorePaths,
    reducer: (state: RootState, paths) => {
      // Used for debugging purposes (hot reloads)
      // if (isDevelopment) {
      //   return state;
      // }

      // TODO: Persist everything except the user state...
      // Is this a good idea in production? It allows people to refresh their browser and not lose progress.
      // But it also means that we may encounter... "weird" bugs with the state.
      return {
        // ...state,
        // setting: state.setting,
        user: {
          // If we want to "remember" the user's username.
          loginEmailInput: state.user.rememberMeToggled ? state.user.loginEmailInput : '',
          rememberMeToggled: state.user.rememberMeToggled
        }
      };
    }
  }),
  SettingPlugin
];

// Add all dev-only plugins
if (isDevelopment) {
  // plugins.push(ActionLoggerPlugin);
  plugins.push(ServerStateLoggerPlugin);
}

/**
 * This logic is used to guard the app navigation and prevent problems from occurring.
 * When navigation occurs, we will show a modal to the user.
 * @param state Root state of the store.
 * @return If true, do not allow the app to navigate.
 */
function isUnsafeToNavigate(state: RootState) {
  // TODO: Actually implement this check
  // Use something like this to get the state
  // context.getters['editBlockPane/isStateDirty']
  // const isStateDirty = state.project.editBlockPane && state.project.editBlockPane.isStateDirty;
  return state.project.hasProjectBeenModified; // || isStateDirty;
}

/**
 * This logic is used to "freeze" the app while a dangerous operation is taking place.
 * @param state Root state of the store.
 * @return If true, show the app as "busy".
 */
function isAppBusy(state: RootState) {
  return state.project.isDeployingProject;
}

export default new Vuex.Store<RootState>({
  getters: {
    isUnsafeToNavigate,
    isAppBusy
  },
  mutations: {},
  actions: {},
  modules: {
    setting: SettingModule,
    deployment: DeploymentViewModule,
    deploymentExecutions: DeploymentExecutionsPaneModule,
    viewBlock: ViewBlockPaneModule,
    viewTransition: ViewTransitionPaneModule,
    project: ProjectView,
    allProjects: AllProjects,
    runLambda: RunLambdaModule,
    toasts: ToastPaneModule,
    user: UserModule,
    billing: BillingPaneModule
  },
  plugins,
  // Dev Only: Causes Vuex to get angry when mutations are done to it's state outside of a mutator
  strict: isDevelopment
});
