import Vue from 'vue';
import BootstrapVue from 'bootstrap-vue';
import VueKonva from 'vue-konva';
import { sync } from 'vuex-router-sync'

import './vendor';

import '@/styles/fonts.scss';
import '@/styles/bootstrap.scss';
import '@/styles/custom-bootstrap-theme.scss';
import '@/styles/app.scss';
import '@/styles/class-helpers.scss';

import App from './App';
import router from './router';
import store from './store/index';
import './registerServiceWorker';

Vue.use(BootstrapVue);
Vue.use(VueKonva);

Vue.config.productionTip = false;

// If, in the future, we need to unsync the router we can use this function.
const unsync = sync(store, router);

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app');
