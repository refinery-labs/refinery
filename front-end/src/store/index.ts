import Vue from 'vue';
import Vuex from 'vuex';
import SettingPlugin from './plugins/setting';
import SettingModule from './modules/setting';
import UserModule from './modules/user';
import createPersistedState from 'vuex-persistedstate';
import ProjectView from './modules/project-view';
import AllProjects from './modules/all-projects';
import {RootState, UserInterfaceSettings} from '@/store/store-types';
import ToastPaneModule from '@/store/modules/toasts';
import ActionLoggerPlugin from '@/store/plugins/action-logger';

Vue.use(Vuex);

const isDevelopment = process.env.NODE_ENV !== 'production';

const persistedStorePaths = [
  'setting',
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
        setting: state.setting,
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
}

export default new Vuex.Store<RootState>({
  mutations: {},
  actions: {},
  modules: {
    setting: SettingModule,
    project: ProjectView,
    allProjects: AllProjects,
    toasts: ToastPaneModule,
    user: UserModule
  },
  plugins,
  // Dev Only: Causes Vuex to get angry when mutations are done to it's state outside of a mutator
  strict: isDevelopment
});
