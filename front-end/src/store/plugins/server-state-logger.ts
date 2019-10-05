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
  }, 5000);

  store.subscribeAction((action, state) => {
    stack.push({
      vueType: 'action',
      localTimestamp: Date.now(),
      ...action
    });
  });

  store.subscribe((mutation, state) => {
    // Special case for when the router changes location
    if (mutation.type === 'route/ROUTE_CHANGED') {
      stack.push({
        vueType: 'route-change',
        localTimestamp: Date.now(),
        fromPath: (mutation.payload && mutation.payload.from && mutation.payload.from.fullPath) || null,
        toPath: (mutation.payload && mutation.payload.to && mutation.payload.to.fullPath) || null
      });
      return;
    }

    stack.push({
      vueType: 'mutation',
      localTimestamp: Date.now(),
      ...mutation
    });
  });
}

export default ServerStateLoggerPlugin;
