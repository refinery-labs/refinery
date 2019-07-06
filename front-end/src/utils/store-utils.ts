import store from '../store/index';
import { deepJSONCopy } from '@/lib/general-utils';
import { EditBlockActions } from '@/store/modules/panes/edit-block-pane';

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

export async function saveEditBlockToProject() {
  await store.dispatch(`project/editBlockPane/${EditBlockActions.saveBlock}`, null, { root: true });
}
