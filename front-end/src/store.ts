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
  ],
  // Dev Only: Causes Vuex to get angry when mutations are done to it's state outside of a mutator
  strict: process.env.NODE_ENV !== 'production'
});
