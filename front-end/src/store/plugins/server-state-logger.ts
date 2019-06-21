import { Store } from 'vuex';
import uuid from 'uuid/v4';
import { RootState } from '@/store/store-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { StashStateLogRequest, StashStateLogResponse } from '@/types/api-types';
import { API_ENDPOINT } from '@/constants/api-constants';

function ServerStateLoggerPlugin(store: Store<RootState>) {
  // This ID persists alongside the browser session.
  const sessionId = uuid();

  let stack: object[] = [];

  setInterval(() => {
    if (stack.length === 0) {
      return;
    }

    makeApiRequest<StashStateLogRequest, StashStateLogResponse>(API_ENDPOINT.StashStateLog, {
      session_id: sessionId,
      state: {
        vueType: 'stack',
        stack
      }
    });

    stack = [];
  }, 1000);

  store.subscribeAction((action, state) => {
    stack.push({
      vueType: 'action',
      localTimestamp: Date.now(),
      ...action
    });
  });

  store.subscribe((mutation, state) => {
    stack.push({
      vueType: 'mutation',
      localTimestamp: Date.now(),
      ...mutation
    });
  });
}

export default ServerStateLoggerPlugin;
