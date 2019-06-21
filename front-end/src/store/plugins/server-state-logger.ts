import { Store } from 'vuex';
import uuid from 'uuid/v4';
import { RootState } from '@/store/store-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { StashStateLogRequest, StashStateLogResponse } from '@/types/api-types';
import { API_ENDPOINT } from '@/constants/api-constants';

function ServerStateLoggerPlugin(store: Store<RootState>) {
  // This ID persists alongside the browser session.
  const sessionId = uuid();

  store.subscribeAction((action, state) => {
    makeApiRequest<StashStateLogRequest, StashStateLogResponse>(API_ENDPOINT.StashStateLog, {
      session_id: sessionId,
      state: {
        vueType: 'action',
        ...action
      }
    });
  });

  store.subscribe((mutation, state) => {
    makeApiRequest<StashStateLogRequest, StashStateLogResponse>(API_ENDPOINT.StashStateLog, {
      session_id: sessionId,
      state: {
        vueType: 'mutation',
        ...mutation
      }
    });
  });
}

export default ServerStateLoggerPlugin;
