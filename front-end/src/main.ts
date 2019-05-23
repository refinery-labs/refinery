import Vue from 'vue';
import BootstrapVue from 'bootstrap-vue';
import VueKonva from 'vue-konva';

import './vendor';

import '@/styles/fonts.scss';
import '@/styles/bootstrap.scss';
import '@/styles/custom-bootstrap-theme.scss';
import '@/styles/app.scss';

import App from './App';
import router from './router';
import store from './store';
import './registerServiceWorker';

Vue.use(BootstrapVue);
Vue.use(VueKonva);

Vue.config.productionTip = false;

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app');
