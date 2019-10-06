import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';

const storeName = 'editSharedFile';

// Types
export interface EditSharedFilePaneState {
  fileName: string;
}

// Initial State
const moduleState: EditSharedFilePaneState = {
  fileName: ''
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class EditSharedFilePaneStore extends VuexModule<ThisType<EditSharedFilePaneState>, RootState>
  implements EditSharedFilePaneState {
  public fileName: string = initialState.fileName;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setSharedFileName(value: string) {
    this.fileName = value;
  }
}

export const EditSharedFilePaneModule = getModule(EditSharedFilePaneStore);
