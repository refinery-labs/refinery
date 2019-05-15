import Vue from 'vue';
import Vuex from 'vuex';
import SettingPlugin from '@/store/plugins/setting';
import SettingModule from '@/store/modules/setting';

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    setting: {
    
    }
  },
  mutations: {},
  actions: {},
  modules: {
    setting: SettingModule
  },
  plugins: [
    SettingPlugin,
  ]
});
