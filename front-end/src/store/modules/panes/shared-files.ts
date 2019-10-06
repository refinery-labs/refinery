import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import store from '@/store';
import { ProjectViewActions } from '@/constants/store-constants';
import { SIDEBAR_PANE } from '@/types/project-editor-types';

const storeName = 'sharedFiles';

// Types
export interface SharedFilesPaneState {
  addSharedFileName: string;
  newSharedFilenameIsValid: boolean | null;
}

// Initial State
const moduleState: SharedFilesPaneState = {
  addSharedFileName: '',
  newSharedFilenameIsValid: null
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class SharedFilesPaneStore extends VuexModule<ThisType<SharedFilesPaneState>, RootState>
  implements SharedFilesPaneState {
  public addSharedFileName: string = initialState.addSharedFileName;
  public newSharedFilenameIsValid: boolean | null = initialState.newSharedFilenameIsValid;

  @Mutation
  public setSharedFileName(value: string) {
    this.addSharedFileName = value;

    if (value.trim() == '') {
      this.newSharedFilenameIsValid = false;
      return;
    }
    this.newSharedFilenameIsValid = true;
  }
}

export const SharedFilesPaneModule = getModule(SharedFilesPaneStore);
