import uuid from 'uuid/v4';
import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import store from '@/store/index';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState } from '@/store/store-types';
import { CreateSavedBlockRequest, CreateSavedBlockResponse, SharedBlockPublishStatus } from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';

const storeName = 'createSavedBlockView';

export interface CreateSavedBlockViewState {
  nameInput: string;
  descriptionInput: string;
  publishStatus: boolean;
  modalVisibility: boolean;
}

export const baseState: CreateSavedBlockViewState = {
  nameInput: '',
  descriptionInput: '',
  publishStatus: false,
  modalVisibility: false
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class CreateSavedBlockViewStore extends VuexModule<ThisType<CreateSavedBlockViewState>, RootState>
  implements CreateSavedBlockViewState {
  public nameInput = initialState.nameInput;
  public descriptionInput = initialState.descriptionInput;
  public publishStatus = initialState.publishStatus;
  public modalVisibility = initialState.modalVisibility;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setName(nameInput: string) {
    this.nameInput = nameInput;
  }

  @Mutation
  public setDescription(descriptionInput: string) {
    this.descriptionInput = descriptionInput;
  }

  @Mutation
  public setPublishStatus(publishStatus: boolean) {
    this.publishStatus = publishStatus;
  }

  @Mutation
  public setModalVisibility(modalVisibility: boolean) {
    this.modalVisibility = modalVisibility;
  }

  @Action
  public openModal() {
    this.setModalVisibility(true);

    // TODO: Copy block from main store?
  }

  @Action
  public closeModal() {
    this.setModalVisibility(false);

    this.resetState();
  }

  @Action
  public async publishBlock() {
    const editBlockPaneStore = this.context.rootState.project.editBlockPane;
    if (!editBlockPaneStore || !editBlockPaneStore.selectedNode) {
      console.error('Unable to publish new block, missing selected block');
      return;
    }

    const response = await makeApiRequest<CreateSavedBlockRequest, CreateSavedBlockResponse>(
      API_ENDPOINT.CreateSavedBlock,
      {
        block_object: editBlockPaneStore.selectedNode,
        description: this.descriptionInput,
        // id: uuid(),
        share_status: this.publishStatus ? SharedBlockPublishStatus.PUBLISHED : SharedBlockPublishStatus.PRIVATE,
        version: 1
      }
    );

    if (!response || !response.success) {
      console.error('Unable to publish block. Server did not return with success');
      return;
    }

    this.closeModal();
  }
}

export const CreateSavedBlockViewStoreModule = getModule(CreateSavedBlockViewStore);
