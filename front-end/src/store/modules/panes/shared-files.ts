import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';

const storeName = 'sharedFiles';

// Types
export interface SharedFilesPaneState {
  addSharedFileName: string;
  newSharedFilenameIsValid: boolean | null;
  searchText: string;
}

// Initial State
const moduleState: SharedFilesPaneState = {
  addSharedFileName: '',
  newSharedFilenameIsValid: null,
  searchText: ''
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class SharedFilesPaneStore extends VuexModule<ThisType<SharedFilesPaneState>, RootState>
  implements SharedFilesPaneState {
  public addSharedFileName: string = initialState.addSharedFileName;
  public newSharedFilenameIsValid: boolean | null = initialState.newSharedFilenameIsValid;
  public searchText: string = initialState.searchText;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setSharedFileName(value: string) {
    this.addSharedFileName = value;

    if (value.trim() == '') {
      this.newSharedFilenameIsValid = false;
      return;
    }
    this.newSharedFilenameIsValid = true;
  }

  @Mutation
  public setSearchText(value: string) {
    this.searchText = value;
  }
}

export const SharedFilesPaneModule = getModule(SharedFilesPaneStore);
