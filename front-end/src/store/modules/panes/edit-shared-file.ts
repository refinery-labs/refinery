import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { LambdaWorkflowState, SupportedLanguage, WorkflowFile } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { SIDEBAR_PANE } from '@/types/project-editor-types';
import { isSharedFileNameValid } from '@/store/modules/panes/shared-files';
import { getLanguageFromFileName } from '@/utils/editor-utils';

const storeName = StoreType.editSharedFile;

// Types
export interface EditSharedFilePaneState {
  fileName: string;
  sharedFile: WorkflowFile | null;
  currentSharedFilePane: SIDEBAR_PANE;
  previousSharedFilePanes: SIDEBAR_PANE[];
  newSharedFilenameIsValid: boolean | null;
}

// Initial State
const moduleState: EditSharedFilePaneState = {
  fileName: '',
  sharedFile: null,
  currentSharedFilePane: SIDEBAR_PANE.sharedFiles,
  previousSharedFilePanes: [SIDEBAR_PANE.sharedFiles],
  newSharedFilenameIsValid: null
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, name: storeName })
export class EditSharedFilePaneStore extends VuexModule<ThisType<EditSharedFilePaneState>, RootState>
  implements EditSharedFilePaneState {
  public fileName: string = initialState.fileName;
  public sharedFile: WorkflowFile | null = initialState.sharedFile;
  public previousSharedFilePanes: SIDEBAR_PANE[] = initialState.previousSharedFilePanes;
  public currentSharedFilePane: SIDEBAR_PANE = initialState.currentSharedFilePane;
  public newSharedFilenameIsValid: boolean | null = initialState.newSharedFilenameIsValid;

  get getFileLanguage(): SupportedLanguage {
    if (this.sharedFile === null) {
      return SupportedLanguage.NODEJS_10;
    }
    return getLanguageFromFileName(this.sharedFile.name);
  }

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setSharedFile(value: WorkflowFile) {
    this.sharedFile = deepJSONCopy(value);
  }

  @Mutation
  public setSharedFileName(value: string) {
    if (!this.sharedFile) {
      console.error("You tried to set the name of something that doesn't exist!");
      return;
    }
    this.newSharedFilenameIsValid = isSharedFileNameValid(value);

    if (!this.newSharedFilenameIsValid) {
      return;
    }
    this.sharedFile.name = value;
  }

  @Mutation
  public setSharedFileBody(value: string) {
    if (!this.sharedFile) {
      console.error("You tried to set the name of something that doesn't exist!");
      return;
    }
    this.sharedFile.body = value;
  }

  @Mutation
  public pushLastSharedFilePaneLocationToHistory(lastSharedFilePane: SIDEBAR_PANE) {
    this.previousSharedFilePanes.push(lastSharedFilePane);
  }

  @Mutation
  public removeLastSharedFilePaneLocationFromHistory() {
    this.previousSharedFilePanes.pop();
  }

  @Mutation
  public setCurrentSharedFilePaneLocation(currentSharedFilePane: SIDEBAR_PANE) {
    this.currentSharedFilePane = currentSharedFilePane;
  }

  @Action
  public async openSharedFile(value: WorkflowFile) {
    this.setSharedFile(value);
    await this.setCurrentSharedFilePane(SIDEBAR_PANE.editSharedFile);
  }

  @Action
  public async saveSharedFile() {
    await this.context.dispatch(`project/${ProjectViewActions.saveSharedFile}`, this.sharedFile, { root: true });
  }

  @Action
  public async deleteSharedFile() {
    await this.context.dispatch(`project/${ProjectViewActions.deleteSharedFile}`, this.sharedFile, { root: true });
    await this.navigateToPreviousSharedFilesPane();
  }

  @Action
  public setCurrentShareFilePaneHistory(sharedFileLocation: SIDEBAR_PANE) {
    if (this.currentSharedFilePane !== sharedFileLocation) {
      this.pushLastSharedFilePaneLocationToHistory(this.currentSharedFilePane);
    }
    this.setCurrentSharedFilePaneLocation(sharedFileLocation);
  }

  @Action
  public async setCurrentSharedFilePane(sharedFileLocation: SIDEBAR_PANE) {
    this.setCurrentShareFilePaneHistory(sharedFileLocation);
    await this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, sharedFileLocation, {
      root: true
    });
  }

  @Action
  public async navigateToPreviousSharedFilesPane() {
    const lastSharedFilePane = this.previousSharedFilePanes[this.previousSharedFilePanes.length - 1];
    this.removeLastSharedFilePaneLocationFromHistory();
    this.setCurrentSharedFilePaneLocation(lastSharedFilePane);
    await this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, lastSharedFilePane, {
      root: true
    });
  }

  @Action
  public async openSharedFileLinks() {
    await this.setCurrentSharedFilePane(SIDEBAR_PANE.editSharedFileLinks);
  }

  @Action
  public async selectCodeBlockToAddSharedFileTo() {
    await this.setCurrentSharedFilePane(SIDEBAR_PANE.addingSharedFileLink);
    await this.context.dispatch(`project/${ProjectViewActions.setIsAddingSharedFileToCodeBlock}`, true, {
      root: true
    });
  }

  @Action
  public async getSharedFile() {
    return deepJSONCopy(this.sharedFile);
  }

  @Action
  public async cancelSelectingCodeBlockToAddSharedFileTo() {
    await this.navigateToPreviousSharedFilesPane();

    await this.context.dispatch(`project/${ProjectViewActions.setIsAddingSharedFileToCodeBlock}`, false, {
      root: true
    });
  }

  @Action
  public async viewCodeBlockSharedFiles(codeBlock: LambdaWorkflowState) {
    await this.context.dispatch(`codeBlockSharedFiles/openCodeBlockSharedFiles`, codeBlock, {
      root: true
    });
  }

  @Action
  public async fileNameChange(fileName: string) {
    this.setSharedFileName(fileName);
    await this.saveSharedFile();
  }

  @Action
  public async codeEditorChange(value: string) {
    this.setSharedFileBody(value);
    await this.saveSharedFile();
  }
}
