import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import {
  CreateSavedBlockRequest,
  CreateSavedBlockResponse,
  SavedBlockStatusCheckResult,
  SharedBlockPublishStatus,
  SavedBlockSaveType
} from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import { ProjectViewActions } from '@/constants/store-constants';
import { LambdaWorkflowState, WorkflowState, WorkflowStateType } from '@/types/graph';
import { EditBlockActions } from '@/store/modules/panes/edit-block-pane';
import { inputDataExample } from '@/constants/saved-block-constants';
import { createBlockDataForPublishedSavedBlock } from '@/utils/block-utils';
import { getSharedFilesForCodeBlock } from '@/utils/project-helpers';

const storeName = StoreType.createSavedBlockView;

export interface CreateSavedBlockViewState {
  nameInput: string | null;
  existingBlockMetadata: SavedBlockStatusCheckResult | null;

  descriptionInput: string | null;
  savedDataInput: string | null;

  publishStatus: boolean;
  publishDisabled: boolean;
  modalVisibility: boolean;
  saveType: SavedBlockSaveType;

  busyPublishingBlock: boolean;
}

export const baseState: CreateSavedBlockViewState = {
  nameInput: null,
  existingBlockMetadata: null,

  descriptionInput: null,
  savedDataInput: inputDataExample,
  publishStatus: false,
  publishDisabled: false,
  modalVisibility: false,
  saveType: SavedBlockSaveType.CREATE,

  busyPublishingBlock: false
};

function isNotEmptyStringButPreserveNull(str: string | null) {
  if (str === null) {
    return null;
  }

  return str !== '';
}

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, name: storeName })
export class CreateSavedBlockViewStore extends VuexModule<ThisType<CreateSavedBlockViewState>, RootState>
  implements CreateSavedBlockViewState {
  public nameInput = initialState.nameInput;
  public existingBlockMetadata = initialState.existingBlockMetadata;

  public descriptionInput = initialState.descriptionInput;
  public savedDataInput = initialState.savedDataInput;

  public publishStatus = initialState.publishStatus;
  public publishDisabled = initialState.publishDisabled;
  public saveType = initialState.saveType;
  public modalVisibility = initialState.modalVisibility;
  public busyPublishingBlock = initialState.busyPublishingBlock;

  get nameInputValid() {
    return isNotEmptyStringButPreserveNull(this.nameInput);
  }

  get descriptionInputValid() {
    return isNotEmptyStringButPreserveNull(this.descriptionInput);
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
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
  public setSavedData(savedDataInput: string) {
    this.savedDataInput = savedDataInput;
  }

  @Mutation
  public setPublishStatus(publishStatus: boolean) {
    this.publishStatus = publishStatus;
  }

  @Mutation
  public setPublishDisabled(publishDisabled: boolean) {
    this.publishDisabled = publishDisabled;
  }

  @Mutation
  public setSaveType(saveType: SavedBlockSaveType) {
    this.saveType = saveType;
  }

  @Mutation
  public setModalVisibility(modalVisibility: boolean) {
    this.modalVisibility = modalVisibility;
  }

  @Mutation
  public setExistingBlockMetadata(existingBlock: SavedBlockStatusCheckResult) {
    this.existingBlockMetadata = existingBlock;
  }

  @Mutation
  public setBusyPublishing(busy: boolean) {
    this.busyPublishingBlock = busy;
  }

  private setPublishState(isForkingBlock: boolean, isPublished: boolean) {
    this.setPublishDisabled(isPublished && !isForkingBlock);
    this.setPublishStatus(isPublished && !isForkingBlock);
  }

  @Action
  public async openModal(saveType: SavedBlockSaveType) {
    // Don't allow this action to happen in Demo Mode
    if (this.context.rootState.project.isInDemoMode) {
      await this.context.dispatch(`unauthViewProject/promptDemoModeSignup`, false, { root: true });
      return;
    }

    this.resetState();

    this.setSaveType(saveType);

    const editBlockPaneState = this.context.rootState.project.editBlockPane;
    if (!editBlockPaneState || !editBlockPaneState.selectedNode) {
      console.error('Unable to begin publish block, missing store');
      return;
    }

    if (editBlockPaneState.selectedNode.type === WorkflowStateType.LAMBDA) {
      const lambdaBlock = editBlockPaneState.selectedNode as LambdaWorkflowState;

      if (lambdaBlock.saved_input_data !== undefined && lambdaBlock.saved_input_data !== null) {
        this.setSavedData(lambdaBlock.saved_input_data);
      }
    }

    const isForkingBlock = saveType === SavedBlockSaveType.FORK;

    const isBlockOwner =
      editBlockPaneState.selectedNodeMetadata && editBlockPaneState.selectedNodeMetadata.is_block_owner;

    if (editBlockPaneState.selectedNode.saved_block_metadata && isBlockOwner) {
      const metadata = editBlockPaneState.selectedNodeMetadata as SavedBlockStatusCheckResult;

      this.setExistingBlockMetadata(metadata);
      // this.setSavedData(metadata.)
      this.setName(metadata.name);
      this.setDescription(metadata.description);

      const isPublished = metadata.share_status === SharedBlockPublishStatus.PUBLISHED;
      this.setPublishState(isForkingBlock, isPublished);

      if (this.saveType !== SavedBlockSaveType.FORK) {
        this.setSaveType(SavedBlockSaveType.UPDATE);
      }
    } else {
      this.setPublishState(isForkingBlock, false);
    }

    this.setModalVisibility(true);
  }

  @Action
  public closeModal() {
    if (this.busyPublishingBlock) {
      console.error('Tried to close publish modal while busy, please wait!');
      return;
    }

    this.setModalVisibility(false);

    this.resetState();
  }

  @Action
  public async publishBlock() {
    const editBlockPaneStore = this.context.rootState.project.editBlockPane;
    if (!editBlockPaneStore || !editBlockPaneStore.selectedNode || !this.context.rootState.project.openedProject) {
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

    this.setBusyPublishing(true);

    const lambdaBlock = editBlockPaneStore.selectedNode as LambdaWorkflowState;

    const savedInputData = this.savedDataInput !== null ? this.savedDataInput : undefined;

    const sharedFiles = getSharedFilesForCodeBlock(
      editBlockPaneStore.selectedNode.id,
      this.context.rootState.project.openedProject
    );

    const request: CreateSavedBlockRequest = {
      block_object: createBlockDataForPublishedSavedBlock(lambdaBlock, this.nameInput, savedInputData),
      description: this.descriptionInput,
      share_status: this.publishStatus ? SharedBlockPublishStatus.PUBLISHED : SharedBlockPublishStatus.PRIVATE,
      version: 1,
      shared_files: sharedFiles,
      save_type: this.saveType
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

      this.setBusyPublishing(false);
      return;
    }

    if (!response.block) {
      console.error('Create saved block did not return a new block');

      this.setBusyPublishing(false);
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

    this.setBusyPublishing(false);

    this.closeModal();
    this.resetState();
  }
}
