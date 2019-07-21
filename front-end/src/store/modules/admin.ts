import { VuexModule, Module, Mutation, Action, getModule } from 'vuex-module-decorators';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState } from '@/store/store-types';

// This is the name that this will be added to the Vuex store with.
// You will need to add to the `RootState` interface if you want to access this state via `rootState` from anywhere.
const storeName = 'admin';

export interface AdminState {
  example: string;
}

export const baseState: AdminState = {
  example: 'delete me'
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, dynamic: true, store, name: storeName })
class AdminStore extends VuexModule<ThisType<AdminState>, RootState> implements AdminState {
  public example: string = initialState.example;

  // Example of "getter" syntax.
  get isAdmin() {
    return this.context.rootState.user.authenticated;
  }

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  // Note: Mutators cannot call other Mutators. If you need to do that, use an Action.
  @Mutation
  public setExample(value: string) {
    this.example = value;
  }

  // This is able to call a Mutator via the `this` context because of magic.
  @Action
  public setExampleViaAction(value: string) {
    this.setExample(value);
  }
}

export const AdminStoreModule = getModule(AdminStore);
