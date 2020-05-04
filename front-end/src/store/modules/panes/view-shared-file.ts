import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { LambdaWorkflowState, SupportedLanguage, WorkflowFile } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { SIDEBAR_PANE } from '@/types/project-editor-types';
import { getLanguageFromFileName } from '@/utils/editor-utils';
import { LoggingAction } from '@/lib/LoggingMutation';

const storeName = StoreType.viewSharedFile;

// Types
export interface ViewSharedFilePaneState {
  sharedFile: WorkflowFile | null;
}

// Initial State
const moduleState: ViewSharedFilePaneState = {
  sharedFile: null
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, name: storeName })
export class ViewSharedFilePaneStore extends VuexModule<ThisType<ViewSharedFilePaneState>, RootState>
  implements ViewSharedFilePaneState {
  public sharedFile: WorkflowFile | null = initialState.sharedFile;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setSharedFile(sharedFile: WorkflowFile) {
    this.sharedFile = sharedFile;
  }

  @LoggingAction
  public viewSharedFile(sharedFile: WorkflowFile) {
    this.setSharedFile(sharedFile);
    this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.viewSharedFile, {
      root: true
    });
  }

  @LoggingAction
  public backToSavedBlockView() {
    this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.addSavedBlock, {
      root: true
    });
  }

  get getFileLanguage(): SupportedLanguage {
    if (this.sharedFile === null) {
      return SupportedLanguage.NODEJS_10;
    }
    return getLanguageFromFileName(this.sharedFile.name);
  }
}
