import { deepJSONCopy } from '@/lib/general-utils';
import { EditBlockActions } from '@/store/modules/panes/edit-block-pane';
import { UserActions } from '@/constants/store-constants';

/**
 * Called by any store to "reset" it's state.
 * @param state Copy of the state of the store
 * @param moduleState The initial
 */
export function resetStoreState(state: any, moduleState: {}) {
  Object.keys(moduleState).forEach(key => {
    // @ts-ignore
    state[key] = deepJSONCopy(moduleState[key]);
  });
}

function getStore() {
  return require('../store/index').default;
}

export async function saveEditBlockToProject() {
  await getStore().dispatch(`project/editBlockPane/${EditBlockActions.saveBlock}`, null, { root: true });
}

export async function signupDemoUser() {
  const store = getStore();

  await store.dispatch(`user/${UserActions.fetchAuthenticationState}`);

  if (store.state.user.authenticated) {
    return true;
  }

  store.commit(`unauthViewProject/setShowSignupModal`, true);
}
