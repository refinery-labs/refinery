import VueNativeSock from 'vue-native-websocket';
import { RootState } from '@/store/store-types';
import { Vue, VueConstructor } from 'vue/types/vue';
import { Store } from 'vuex';

export function setupWebsocketVuePlugin(Vue: VueConstructor, store: Store<RootState>) {
  const websocketEndpoint =
    `${process.env.VUE_APP_API_HOST}`.replace('https://', 'wss://').replace('http://', 'ws://') +
    '/ws/v1/lambdas/livedebug';

  const mutations = {
    SOCKET_ONOPEN: 'runLambda/SOCKET_ONOPEN',
    SOCKET_ONCLOSE: 'runLambda/SOCKET_ONCLOSE',
    SOCKET_ONERROR: 'runLambda/SOCKET_ONERROR',
    SOCKET_ONMESSAGE: 'runLambda/SOCKET_ONMESSAGE',
    SOCKET_RECONNECT: 'runLambda/SOCKET_RECONNECT',
    SOCKET_RECONNECT_ERROR: 'runLambda/SOCKET_RECONNECT_ERROR'
  };

  Vue.use(VueNativeSock, websocketEndpoint, {
    store: store,
    reconnection: true,
    mutations: mutations
  });
}
