import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { EditSharedFilePaneModule } from '@/store';
import { LambdaWorkflowState } from '@/types/graph';

const storeName = StoreType.editSharedFileLinks;

// Types
export interface EditSharedFileLinksPaneState {}

// Initial State
const moduleState: EditSharedFileLinksPaneState = {};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, name: storeName })
export class EditSharedFileLinksPaneStore extends VuexModule<ThisType<EditSharedFileLinksPaneState>, RootState>
  implements EditSharedFileLinksPaneState {
  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }
}
