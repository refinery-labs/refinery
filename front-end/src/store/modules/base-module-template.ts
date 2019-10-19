import { VuexModule, Module, Mutation, Action, getModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';

// ####### NOTICE ME, SENPAI! #######
// Follow the instructions in `src/store/store-accessor.ts` for everything you need to do to add another store.
// Delete this text when you are done!
// ####### THANK YOU, SENPAI! #######

// Add a new enum value to StoreType and put that below, then delete this text. :)
const storeName = StoreType.addSavedBlockPane;

export interface ExampleBaseState {
  example: string;
}

export const baseState: ExampleBaseState = {
  example: 'delete me'
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, name: storeName })
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
  @Action
  public setExampleViaAction(value: string) {
    this.setExample(value);
  }
}
