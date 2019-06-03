import Vue from 'vue';
import Vuex from 'vuex';
import SettingPlugin from './plugins/setting';
import SettingModule from './modules/setting';
import UserModule from './modules/user';
import createPersistedState from 'vuex-persistedstate';
import ProjectView from './modules/project-view';
import AllProjects from './modules/all-projects';
import {RootState, UserInterfaceSettings} from '@/store/store-types';

Vue.use(Vuex);

// states which we don't want to persist.
const whiteListedStates = [
  UserInterfaceSettings.isFixed,
  UserInterfaceSettings.isBoxed,
  UserInterfaceSettings.isGlobalNavCollapsed,
  UserInterfaceSettings.isSidebarCollapsed,
  UserInterfaceSettings.asideHover,
  UserInterfaceSettings.asideScrollbar,
  UserInterfaceSettings.asideToggled,
  UserInterfaceSettings.hiddenFooter,
  UserInterfaceSettings.isCollapsedText,
  UserInterfaceSettings.isFloat,
  UserInterfaceSettings.useFullLayout
];

const isDevelopment = process.env.NODE_ENV !== 'production';

const persistedStorePaths = [
  'setting',
  // 'project',
  // 'allProjects',
  'user.loginEmailInput',
  'user.rememberMeToggled'
];

export default new Vuex.Store<RootState>({
  mutations: {},
  actions: {},
  modules: {
    setting: SettingModule,
    project: ProjectView,
    allProjects: AllProjects,
    user: UserModule
  },
  plugins: [
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
  ],
  // Dev Only: Causes Vuex to get angry when mutations are done to it's state outside of a mutator
  strict: isDevelopment
});
