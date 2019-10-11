import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';
import { WorkflowFile, WorkflowRelationshipType } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';

const storeName = 'editSharedFileLinks';

// Types
export interface EditSharedFileLinksPaneState {}

// Initial State
const moduleState: EditSharedFileLinksPaneState = {};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class EditSharedFileLinksPaneStore extends VuexModule<ThisType<EditSharedFileLinksPaneState>, RootState>
  implements EditSharedFileLinksPaneState {
  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }
}

export const EditSharedFileLinksPaneModule = getModule(EditSharedFileLinksPaneStore);
