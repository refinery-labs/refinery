import { ProjectViewGetters } from '@/constants/store-constants';

import Vue from 'vue';

// Must be called before any components are loaded
import './lib/class-component-hooks';

import BootstrapVue from 'bootstrap-vue';
import VueIntercom from 'vue-intercom';
import { sync } from 'vuex-router-sync';

import('./vendor');

import '@/styles/fonts.scss';
import '@/styles/bootstrap.scss';
import '@/styles/custom-bootstrap-theme.scss';
import '@/styles/app.scss';
import '@/styles/class-helpers.scss';

import store from './store/index';
import App from './App';
import router from './router';
import('./registerServiceWorker');
import { setupWebsocketVuePlugin } from '@/setup-websocket';

Vue.use(BootstrapVue);
Vue.use(VueIntercom, { appId: 'sjaaunj7' });

Vue.config.productionTip = false;

setupWebsocketVuePlugin(Vue, store);

// If, in the future, we need to unsync the router we can use this function.
const unsync = sync(store, router);

window.onbeforeunload = function(e: Event) {
  if (store.getters[`project/${ProjectViewGetters.canSaveProject}`]) {
    e.preventDefault();
    // This is the spec according to:
    // https://developer.mozilla.org/en-US/docs/Web/API/WindowEventHandlers/onbeforeunload
    // @ts-ignore
    e.returnValue = 'Warning: You have unsaved changes that will be discarded. Are you sure you want to leave?';
  }
};

const vm = new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app');
