import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import { CreateSavedBlockViewStoreModule } from '@/store/modules/panes/create-saved-block-view';
import { CreateSavedBlockViewProps } from '@/types/component-types';
import CreateSavedBlockView from '@/components/ProjectEditor/saved-blocks-components/CreateSavedBlockView';

export interface CreateSavedBlockViewContainerProps {
  modalMode: boolean;
}

@Component
export default class CreateSavedBlockViewContainer extends Vue implements CreateSavedBlockViewContainerProps {
  @Prop({ required: true }) public modalMode!: boolean;

  render() {
    const createSavedBlockViewProps: CreateSavedBlockViewProps = {
      modalMode: this.modalMode,
      existingBlockMetadata: CreateSavedBlockViewStoreModule.existingBlockMetadata,
      descriptionInput: CreateSavedBlockViewStoreModule.descriptionInput,
      descriptionInputValid: CreateSavedBlockViewStoreModule.descriptionInputValid,
      modalVisibility: CreateSavedBlockViewStoreModule.modalVisibility,
      nameInput: CreateSavedBlockViewStoreModule.nameInput,
      nameInputValid: CreateSavedBlockViewStoreModule.nameInputValid,
      publishBlock: CreateSavedBlockViewStoreModule.publishBlock,
      publishStatus: CreateSavedBlockViewStoreModule.publishStatus,
      setDescription: CreateSavedBlockViewStoreModule.setDescription,
      setModalVisibility: CreateSavedBlockViewStoreModule.setModalVisibility,
      setName: CreateSavedBlockViewStoreModule.setName,
      setPublishStatus: CreateSavedBlockViewStoreModule.setPublishStatus
    };

    return <CreateSavedBlockView props={createSavedBlockViewProps} />;
  }
}
