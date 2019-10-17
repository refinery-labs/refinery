import { VuexModule, Module, Mutation, Action, getModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';

const storeName = StoreType.conflictNotifier;

export interface ConflictNotifierState {
  conflictDetected: boolean;
}

export const baseState: ConflictNotifierState = {
  conflictDetected: false
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, name: storeName })
export class ConflictNotifierStore extends VuexModule<ThisType<ConflictNotifierState>, RootState>
  implements ConflictNotifierState {
  public conflictDetected: boolean = initialState.conflictDetected;

  // Example of "getter" syntax.
  // get currentExampleValue() {
  //   return this.example;
  // }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public setConflictDetected(value: boolean) {
    this.conflictDetected = value;
  }

  @Action
  public checkForConflict(value: string) {
    // this.setExample(value);
  }
}
