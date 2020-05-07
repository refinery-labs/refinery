import { VuexModule, Module, Mutation, Action } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { LoggingAction } from '@/lib/LoggingMutation';

// You will need to add to the `RootState` interface if you want to access this state via `rootState` from anywhere.

export interface ExampleBaseState {
  example: string;
}

export const baseState: ExampleBaseState = {
  example: 'delete me'
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, name: 'REPLACE_THIS_WITH StoreType.BaseState < and BaseState is your name' })
export class ExampleBaseStore extends VuexModule<ThisType<ExampleBaseState>, RootState> implements ExampleBaseState {
  public example: string = initialState.example;

  // Example of "getter" syntax.
  get currentExampleValue() {
    return this.example;
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  // Note: Mutators cannot call other Mutators. If you need to do that, use an Action.
  @Mutation
  public setExample(value: string) {
    this.example = value;
  }

  // This is able to call a Mutator via the `this` context because of magic.
  @LoggingAction
  public setExampleViaAction(value: string) {
    this.setExample(value);
  }
}
