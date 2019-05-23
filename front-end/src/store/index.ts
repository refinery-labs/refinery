import Vue from 'vue';
import Vuex from 'vuex';
import SettingPlugin from './plugins/setting';
import SettingModule from './modules/setting';
import createPersistedState from 'vuex-persistedstate';
import ProjectView from './modules/project-view';

Vue.use(Vuex);

// states which we don't want to persist.
const ignoredStates = [
  // Feels bad to have the sidebar re-open on reload... Make this toggleable in the future?
  // 'offsidebarOpen',
  // 'asideToggled',
  'horizontal'
];

export default new Vuex.Store({
  state: {
    setting: {}
  },
  mutations: {},
  actions: {},
  modules: {
    setting: SettingModule,
    project: ProjectView
  },
  plugins: [
    createPersistedState({
      reducer: (persistedState) => {
        // deep clone
        const stateFilter = JSON.parse(JSON.stringify(persistedState));
      
        ignoredStates.forEach(item => delete stateFilter.setting[item]);
        return stateFilter;
      }
    }),
    SettingPlugin
  ],
  // Dev Only: Causes Vuex to get angry when mutations are done to it's state outside of a mutator
  strict: process.env.NODE_ENV !== 'production'
});
