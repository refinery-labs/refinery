import { deepJSONCopy } from '@/lib/general-utils';

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
