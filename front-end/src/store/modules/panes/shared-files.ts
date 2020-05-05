import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { AddSharedFileArguments } from '@/types/shared-files';
import { EditSharedFilePaneModule, SharedFilesPaneModule } from '@/store';
import { ProjectViewActions } from '@/constants/store-constants';
import { SIDEBAR_PANE } from '@/types/project-editor-types';

const storeName = StoreType.sharedFiles;

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

const validFileNameRegex = /^[a-zA-Z0-9_\-.]+$/;

export function isSharedFileNameValid(fileName: string) {
  if (fileName === '') {
    return null;
  }

  if (fileName.trim() == '' || !validFileNameRegex.test(fileName)) {
    return false;
  }

  return true;
}

@Module({ namespaced: true, name: storeName })
export class SharedFilesPaneStore extends VuexModule<ThisType<SharedFilesPaneState>, RootState>
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
    this.newSharedFilenameIsValid = isSharedFileNameValid(value);
  }

  @Mutation
  public setSearchText(value: string) {
    this.searchText = value;
  }

  @Action
  public resetPane() {
    this.resetState();
  }

  @Action
  public async addNewSharedFile() {
    const newSharedFile = await this.context.dispatch(
      `project/${ProjectViewActions.addSharedFile}`,
      {
        name: this.addSharedFileName,
        body: ''
      },
      {
        root: true
      }
    );
    await EditSharedFilePaneModule.openSharedFile(newSharedFile);
    SharedFilesPaneModule.resetState();
  }
}
