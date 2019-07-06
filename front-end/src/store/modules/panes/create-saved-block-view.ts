import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import store from '@/store/index';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState } from '@/store/store-types';
import {
  CreateSavedBlockRequest,
  CreateSavedBlockResponse,
  SavedBlockStatusCheckResult,
  SharedBlockPublishStatus
} from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import { ProjectViewActions } from '@/constants/store-constants';
import { WorkflowState } from '@/types/graph';
import { EditBlockActions } from '@/store/modules/panes/edit-block-pane';

const storeName = 'createSavedBlockView';

export interface CreateSavedBlockViewState {
  nameInput: string | null;
  existingBlockMetadata: SavedBlockStatusCheckResult | null;

  descriptionInput: string | null;

  publishStatus: boolean;
  modalVisibility: boolean;
}

export const baseState: CreateSavedBlockViewState = {
  nameInput: null,
  existingBlockMetadata: null,

  descriptionInput: null,
  publishStatus: false,
  modalVisibility: false
};

function isNotEmptyStringButPreserveNull(str: string | null) {
  if (str === null) {
    return null;
  }

  return str !== '';
}

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class CreateSavedBlockViewStore extends VuexModule<ThisType<CreateSavedBlockViewState>, RootState>
  implements CreateSavedBlockViewState {
  public nameInput = initialState.nameInput;
  public existingBlockMetadata = initialState.existingBlockMetadata;

  public descriptionInput = initialState.descriptionInput;

  public publishStatus = initialState.publishStatus;
  public modalVisibility = initialState.modalVisibility;

  get nameInputValid() {
    return isNotEmptyStringButPreserveNull(this.nameInput);
  }

  get descriptionInputValid() {
    return isNotEmptyStringButPreserveNull(this.descriptionInput);
  }

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

  @Mutation
  public setExistingBlockMetadata(existingBlock: SavedBlockStatusCheckResult) {
    this.existingBlockMetadata = existingBlock;
  }

  @Action
  public openModal() {
    // TODO: Copy block from main store?

    const editBlockPaneState = this.context.rootState.project.editBlockPane;
    if (!editBlockPaneState || !editBlockPaneState.selectedNode) {
      console.error('Unable to begin publish block, missing store');
      return;
    }

    const isBlockOwner =
      editBlockPaneState.selectedNodeMetadata && editBlockPaneState.selectedNodeMetadata.is_block_owner;

    if (editBlockPaneState.selectedNode.saved_block_metadata && isBlockOwner) {
      const metadata = editBlockPaneState.selectedNodeMetadata as SavedBlockStatusCheckResult;

      this.setExistingBlockMetadata(metadata);
      this.setName(metadata.name);
      this.setDescription(metadata.description);
      this.setPublishStatus(metadata.share_status === SharedBlockPublishStatus.PUBLISHED);
    }

    this.setModalVisibility(true);
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

    if (!this.nameInputValid || this.nameInput === null) {
      console.error('Invalid name specified while attempting to create saved block');
      return;
    }

    if (!this.descriptionInputValid || this.descriptionInput === null) {
      console.error('Invalid description specified while attempting to create saved block');
      return;
    }

    const request: CreateSavedBlockRequest = {
      block_object: {
        ...editBlockPaneStore.selectedNode,
        name: this.nameInput
      },
      description: this.descriptionInput,
      share_status: this.publishStatus ? SharedBlockPublishStatus.PUBLISHED : SharedBlockPublishStatus.PRIVATE,
      version: 1
    };

    if (this.existingBlockMetadata) {
      request.id = this.existingBlockMetadata.id;
      request.version = undefined;
    }

    const response = await makeApiRequest<CreateSavedBlockRequest, CreateSavedBlockResponse>(
      API_ENDPOINT.CreateSavedBlock,
      request
    );

    if (!response || !response.success) {
      console.error('Unable to publish block. Server did not return with success');
      return;
    }

    if (!response.block) {
      console.error('Create saved block did not return a new block');
      return;
    }

    const block = response.block;

    const newNode: WorkflowState = {
      ...editBlockPaneStore.selectedNode,
      saved_block_metadata: {
        id: block.id,
        timestamp: block.timestamp,
        version: block.version,
        added_timestamp: Date.now()
      }
    };

    await this.context.dispatch(`project/${ProjectViewActions.updateExistingBlock}`, newNode, { root: true });
    await this.context.dispatch(`project/editBlockPane/${EditBlockActions.selectNodeFromOpenProject}`, newNode.id, {
      root: true
    });

    this.closeModal();
  }
}

export const CreateSavedBlockViewStoreModule = getModule(CreateSavedBlockViewStore);
