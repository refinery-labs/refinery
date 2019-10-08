import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';
import { LambdaWorkflowState, WorkflowFile } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { SIDEBAR_PANE } from '@/types/project-editor-types';

const storeName = 'editSharedFile';

// Types
export interface EditSharedFilePaneState {
  fileName: string;
  sharedFile: WorkflowFile | null;
  currentSharedFilePane: SIDEBAR_PANE;
  previousSharedFilePanes: SIDEBAR_PANE[];
}

// Initial State
const moduleState: EditSharedFilePaneState = {
  fileName: '',
  sharedFile: null,
  currentSharedFilePane: SIDEBAR_PANE.sharedFiles,
  previousSharedFilePanes: [SIDEBAR_PANE.sharedFiles]
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class EditSharedFilePaneStore extends VuexModule<ThisType<EditSharedFilePaneState>, RootState>
  implements EditSharedFilePaneState {
  public fileName: string = initialState.fileName;
  public sharedFile: WorkflowFile | null = initialState.sharedFile;
  public previousSharedFilePanes: SIDEBAR_PANE[] = initialState.previousSharedFilePanes;
  public currentSharedFilePane: SIDEBAR_PANE = initialState.currentSharedFilePane;

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
    this.setCurrentSharedFilePane(SIDEBAR_PANE.editSharedFile);
  }

  @Action
  public async saveSharedFile() {
    await this.context.dispatch(`project/${ProjectViewActions.saveSharedFile}`, this.sharedFile, { root: true });
  }

  @Action
  public async deleteSharedFile() {
    await this.context.dispatch(`project/${ProjectViewActions.deleteSharedFile}`, this.sharedFile, { root: true });
    this.navigateToPreviousSharedFilesPane();
  }

  @Action setCurrentSharedFilePane(sharedFileLocation: SIDEBAR_PANE) {
    this.pushLastSharedFilePaneLocationToHistory(this.currentSharedFilePane);
    this.setCurrentSharedFilePaneLocation(sharedFileLocation);
    this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, sharedFileLocation, {
      root: true
    });
  }

  @Action
  public async navigateToPreviousSharedFilesPane() {
    const lastSharedFilePane = this.previousSharedFilePanes[this.previousSharedFilePanes.length - 1];
    this.removeLastSharedFilePaneLocationFromHistory();
    this.setCurrentSharedFilePaneLocation(lastSharedFilePane);
    this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, lastSharedFilePane, {
      root: true
    });
  }

  @Action
  public async openSharedFileLinks() {
    this.setCurrentSharedFilePane(SIDEBAR_PANE.editSharedFileLinks);
  }

  @Action
  public async selectCodeBlockToAddSharedFileTo() {
    this.setCurrentSharedFilePane(SIDEBAR_PANE.addingSharedFileLink);
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
    this.navigateToPreviousSharedFilesPane();

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
}

export const EditSharedFilePaneModule = getModule(EditSharedFilePaneStore);
