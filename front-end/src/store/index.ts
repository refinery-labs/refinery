import Vue from 'vue';
import Vuex from 'vuex';
import createPersistedState from 'vuex-persistedstate';

import SettingModule from './modules/setting';
import SettingPlugin from './plugins/setting';

Vue.use(Vuex);

export default new Vuex.Store({
    modules: {
        setting: SettingModule
    },
    plugins: [
        createPersistedState({
            reducer: (persistedState) => {
                // deep clone
                const stateFilter = JSON.parse(JSON.stringify(persistedState));
                
                // states which we don't want to persist.
                ['offsidebarOpen', 'asideToggled', 'horizontal']
                    .forEach(item => delete stateFilter.setting[item]);
                return stateFilter
            }
        }),
        SettingPlugin
    ]
})