import Vue from 'vue';
import Vuex from 'vuex';
import SettingPlugin from './plugins/setting';
import SettingModule from './modules/setting';
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

export default new Vuex.Store<RootState>({
  mutations: {},
  actions: {},
  modules: {
    setting: SettingModule,
    project: ProjectView,
    allProjects: AllProjects
  },
  plugins: [
    // TODO: This is busted... Dang
    // createPersistedState({
    //   reducer: (persistedState: RootState) => {
    //     // deep clone
    //     const stateFilter: RootState = JSON.parse(JSON.stringify(persistedState));
    //
    //     // Ignoring the typescript checks here because we know that this is
    //     const newState = Object.keys(stateFilter.setting).reduce((out, key) => {
    //       // @ts-ignore
    //       if (whiteListedStates[key]) {
    //         // @ts-ignore
    //         out[key] = stateFilter.setting[key];
    //       }
    //       return out;
    //     }, {});
    //
    //     return {setting: newState};
    //   }
    // }),
    SettingPlugin
  ],
  // Dev Only: Causes Vuex to get angry when mutations are done to it's state outside of a mutator
  strict: process.env.NODE_ENV !== 'production'
});
