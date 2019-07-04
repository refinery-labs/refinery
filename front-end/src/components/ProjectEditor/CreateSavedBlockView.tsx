import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { CreateSavedBlockViewStoreModule } from '@/store/modules/panes/create-saved-block-view';
import { CreateSavedBlockViewProps } from '@/types/component-types';

@Component
export default class CreateSavedBlockView extends Vue implements CreateSavedBlockViewProps {
  @Prop({ required: true }) public modalMode!: boolean;

  renderContents() {
    return (
      <b-form on={{ submit: preventDefaultWrapper(CreateSavedBlockViewStoreModule.publishBlock) }}>
        <b-form-group
          class="padding-bottom--normal-small margin-bottom--normal-small"
          description="Please specify some text to search for saved blocks with."
        >
          <label class="d-block">Block Name:</label>
          <b-form-input
            type="text"
            autofocus={true}
            required={true}
            state={CreateSavedBlockViewStoreModule.nameInputValid}
            value={CreateSavedBlockViewStoreModule.nameInput}
            on={{ input: CreateSavedBlockViewStoreModule.setName }}
            placeholder="eg, Daily Timer"
          />
          <b-form-invalid-feedback state={CreateSavedBlockViewStoreModule.nameInputValid}>
            Name must not be empty
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          class="padding-bottom--normal-small margin-bottom--normal-small"
          description="Please specify a description for future reference."
        >
          <label class="d-block">Description:</label>
          <b-form-textarea
            size="sm"
            required={true}
            state={CreateSavedBlockViewStoreModule.descriptionInputValid}
            value={CreateSavedBlockViewStoreModule.descriptionInput}
            on={{ input: CreateSavedBlockViewStoreModule.setDescription }}
            placeholder="eg, This block will fire every day (24 hours) and should be used for jobs that run daily."
          />
          <b-form-invalid-feedback state={CreateSavedBlockViewStoreModule.descriptionInputValid}>
            Description must not be empty
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group
          class="padding-bottom--normal-small margin-bottom--normal-small"
          description="This will make the block available for other people to use. Only publish blocks that you are okay with other people seeing!"
        >
          <b-form-checkbox
            class="mr-sm-2 mb-sm-0"
            on={{
              change: () =>
                CreateSavedBlockViewStoreModule.setPublishStatus(!CreateSavedBlockViewStoreModule.publishStatus)
            }}
            checked={CreateSavedBlockViewStoreModule.publishStatus}
          >
            Publish to Refinery Marketplace?
          </b-form-checkbox>
        </b-form-group>
        <div class="text-align--center">
          <b-button variant="primary" class="col-lg-8 mt-3" type="submit">
            Publish Block
          </b-button>
        </div>
      </b-form>
    );
  }

  renderModal() {
    const modalOnHandlers = {
      hidden: () => CreateSavedBlockViewStoreModule.setModalVisibility(false)
    };

    return (
      <b-modal
        on={modalOnHandlers}
        hide-footer={true}
        title="Create New Saved Block"
        visible={CreateSavedBlockViewStoreModule.modalVisibility}
      >
        {this.renderContents()}
      </b-modal>
    );
  }

  render() {
    if (this.modalMode) {
      return this.renderModal();
    }

    return <div>{this.renderContents()}</div>;
  }
}
