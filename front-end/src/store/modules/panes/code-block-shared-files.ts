import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';
import { LambdaWorkflowState, WorkflowFile, WorkflowRelationshipType } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import { AddSharedFileLinkArguments } from '@/types/shared-files';

const storeName = 'codeBlockSharedFiles';

// Types
export interface CodeBlockSharedFilesPaneState {
  codeBlock: LambdaWorkflowState | null;
}

// Initial State
const moduleState: CodeBlockSharedFilesPaneState = {
  codeBlock: null
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class CodeBlockSharedFilesPaneStore extends VuexModule<ThisType<CodeBlockSharedFilesPaneState>, RootState>
  implements CodeBlockSharedFilesPaneState {
  public codeBlock: LambdaWorkflowState | null = initialState.codeBlock;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setCodeBlock(codeBlock: LambdaWorkflowState) {
    this.codeBlock = deepJSONCopy(codeBlock);
  }

  @Action
  public async openCodeBlockSharedFiles(codeBlock: LambdaWorkflowState) {
    this.setCodeBlock(codeBlock);
    EditSharedFilePaneModule.setCurrentSharedFilePane(SIDEBAR_PANE.codeBlockSharedFiles);
  }

  @Action
  public async addSharedFileToCodeBlock(sharedFile: WorkflowFile) {
    if (CodeBlockSharedFilesPaneModule.codeBlock === null) {
      console.error('No Code Block is selected.');
      return;
    }

    const addSharedFileLinkArgs: AddSharedFileLinkArguments = {
      file_id: sharedFile.id,
      node: CodeBlockSharedFilesPaneModule.codeBlock.id,
      path: ''
    };

    return this.context.dispatch(`project/${ProjectViewActions.addSharedFileLink}`, addSharedFileLinkArgs, {
      root: true
    });
  }
}

export const CodeBlockSharedFilesPaneModule = getModule(CodeBlockSharedFilesPaneStore);
