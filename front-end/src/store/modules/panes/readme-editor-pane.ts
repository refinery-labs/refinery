import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { RefineryProject, WorkflowFile } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { OpenProjectMutation, SIDEBAR_PANE } from '@/types/project-editor-types';

const storeName = StoreType.readmeEditor;

// Types
export interface ReadmeEditorPaneState {
  isFullScreenEditorModalVisible: boolean;
}

// Initial State
const moduleState: ReadmeEditorPaneState = {
  isFullScreenEditorModalVisible: false
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, name: storeName })
export class ReadmeEditorPaneStore extends VuexModule<ThisType<ReadmeEditorPaneState>, RootState>
  implements ReadmeEditorPaneState {
  public isFullScreenEditorModalVisible: boolean = initialState.isFullScreenEditorModalVisible;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setFullScreenEditorModalVisibility(isFullScreenEditorModalVisible: boolean) {
    this.isFullScreenEditorModalVisible = isFullScreenEditorModalVisible;
  }

  @Action
  public setFullScreenEditorModalVisibilityAction(isFullScreenEditorModalVisible: boolean) {
    this.setFullScreenEditorModalVisibility(isFullScreenEditorModalVisible);
  }

  @Action
  public async setReadmeContents(readmeString: string) {
    const project = this.context.rootState.project.openedProject;

    if (project === null) {
      console.error('Cant set README, no project is open!');
      return;
    }

    const newProject: RefineryProject = {
      ...project,
      readme: readmeString
    };

    const params: OpenProjectMutation = {
      project: newProject,
      config: null,
      markAsDirty: true
    };

    await this.context.dispatch(`project/${ProjectViewActions.updateProject}`, params, { root: true });
  }
}
