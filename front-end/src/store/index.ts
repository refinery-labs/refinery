import Vue from 'vue';
import Vuex from 'vuex';
import createPersistedState from 'vuex-persistedstate';

import SettingModule from './modules/setting';
import SettingPlugin from './plugins/setting';

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
  ]
});