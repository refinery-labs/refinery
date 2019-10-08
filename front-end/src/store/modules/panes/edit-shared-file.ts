import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';
import { LambdaWorkflowState, WorkflowFile, WorkflowRelationshipType } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import { CodeBlockSharedFilesPaneModule } from '@/store/modules/panes/code-block-shared-files';

const storeName = 'editSharedFile';

// Types
export interface EditSharedFilePaneState {
  fileName: string;
  sharedFile: WorkflowFile | null;
}

// Initial State
const moduleState: EditSharedFilePaneState = {
  fileName: '',
  sharedFile: null
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class EditSharedFilePaneStore extends VuexModule<ThisType<EditSharedFilePaneState>, RootState>
  implements EditSharedFilePaneState {
  public fileName: string = initialState.fileName;
  public sharedFile: WorkflowFile | null = initialState.sharedFile;

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

  @Action
  public async openSharedFile(value: WorkflowFile) {
    this.setSharedFile(value);
    await this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.editSharedFile, {
      root: true
    });
  }

  @Action
  public async saveSharedFile() {
    await this.context.dispatch(`project/${ProjectViewActions.saveSharedFile}`, this.sharedFile, { root: true });
  }

  @Action
  public async deleteSharedFile() {
    await this.context.dispatch(`project/${ProjectViewActions.deleteSharedFile}`, this.sharedFile, { root: true });
    await this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.sharedFiles, {
      root: true
    });
  }

  @Action
  public async navigateBackToSharedFiles() {
    await this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.sharedFiles, {
      root: true
    });
  }

  @Action
  public async openSharedFileLinks() {
    await this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.editSharedFileLinks, {
      root: true
    });
  }

  @Action
  public async selectCodeBlockToAddSharedFileTo() {
    await this.context.dispatch(
      `project/${ProjectViewActions.openLeftSidebarPane}`,
      SIDEBAR_PANE.addingSharedFileLink,
      {
        root: true
      }
    );
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
    await this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.editSharedFile, {
      root: true
    });

    await this.context.dispatch(`project/${ProjectViewActions.setIsAddingSharedFileToCodeBlock}`, false, {
      root: true
    });
  }

  @Action
  public async viewCodeBlockSharedFiles(codeBlock: LambdaWorkflowState) {
    await this.context.dispatch(`codeBlockSharedFiles/setCodeBlockAction`, codeBlock, {
      root: true
    });
  }
}

export const EditSharedFilePaneModule = getModule(EditSharedFilePaneStore);
