import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import { CreateSavedBlockViewProps } from '@/types/component-types';
import CreateSavedBlockView from '@/components/ProjectEditor/saved-blocks-components/CreateSavedBlockView';
import { CreateSavedBlockViewStoreModule } from '@/store';

export interface CreateSavedBlockViewContainerProps {
  modalMode: boolean;
}

@Component
export default class CreateSavedBlockViewContainer extends Vue implements CreateSavedBlockViewContainerProps {
  @Prop({ required: true }) public modalMode!: boolean;

  render() {
    const createSavedBlockViewProps: CreateSavedBlockViewProps = {
      modalMode: this.modalMode,
      isBusyPublishing: CreateSavedBlockViewStoreModule.busyPublishingBlock,
      existingBlockMetadata: CreateSavedBlockViewStoreModule.existingBlockMetadata,
      descriptionInput: CreateSavedBlockViewStoreModule.descriptionInput,
      descriptionInputValid: CreateSavedBlockViewStoreModule.descriptionInputValid,
      modalVisibility: CreateSavedBlockViewStoreModule.modalVisibility,
      blockSaveType: CreateSavedBlockViewStoreModule.saveType,
      nameInput: CreateSavedBlockViewStoreModule.nameInput,
      nameInputValid: CreateSavedBlockViewStoreModule.nameInputValid,
      savedDataInput: CreateSavedBlockViewStoreModule.savedDataInput,
      publishBlock: CreateSavedBlockViewStoreModule.publishBlock,
      publishStatus: CreateSavedBlockViewStoreModule.publishStatus,
      setDescription: CreateSavedBlockViewStoreModule.setDescription,
      setModalVisibility: CreateSavedBlockViewStoreModule.setModalVisibility,
      setName: CreateSavedBlockViewStoreModule.setName,
      setSavedDataInput: CreateSavedBlockViewStoreModule.setSavedData,
      setPublishStatus: CreateSavedBlockViewStoreModule.setPublishStatus
    };

    return <CreateSavedBlockView props={createSavedBlockViewProps} />;
  }
}
