import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { CreateSavedBlockViewProps } from '@/types/component-types';
import { SavedBlockStatusCheckResult, SharedBlockPublishStatus } from '@/types/api-types';

const editModeTitle = 'Update Saved Block Version';
const addModeTitle = 'Create New Saved Block';

const alreadyPublishedText =
  'This option is disabled. You cannot make a published block private again. If you have done this accidentally and need this block unpublished, please contact support';
const newPublishText =
  'This will make the block available for other people to use. Only publish blocks that you are okay with other people seeing! You cannot remove a public block without contacting support.';

@Component
export default class CreateSavedBlockView extends Vue implements CreateSavedBlockViewProps {
  @Prop({ required: true }) descriptionInput!: string | null;
  @Prop({ required: true }) existingBlockMetadata!: SavedBlockStatusCheckResult | null;
  @Prop({ required: true }) descriptionInputValid!: boolean;
  @Prop({ required: true }) nameInput!: string | null;
  @Prop({ required: true }) nameInputValid!: boolean;
  @Prop({ required: true }) publishBlock!: () => void;
  @Prop({ required: true }) publishStatus!: boolean;
  @Prop({ required: true }) setDescription!: (s: string) => void;
  @Prop({ required: true }) setName!: (s: string) => void;
  @Prop({ required: true }) setPublishStatus!: (s: boolean) => void;
  @Prop({ required: true }) public modalMode!: boolean;

  @Prop() modalVisibility?: boolean;
  @Prop() setModalVisibility?: (b: boolean) => void;

  getPublishDisabled() {
    if (!this.existingBlockMetadata) {
      return false;
    }

    return this.existingBlockMetadata.share_status === SharedBlockPublishStatus.PUBLISHED;
  }

  renderContents() {
    const hasExistingBlock = this.existingBlockMetadata !== null;
    const publishDisabled = this.getPublishDisabled();

    return (
      <b-form on={{ submit: preventDefaultWrapper(this.publishBlock) }}>
        <b-form-group
          class="padding-bottom--normal-small margin-bottom--normal-small"
          description="Please fill out the form to create a new saved block."
        >
          <label class="d-block">Block Name:</label>
          <b-form-input
            type="text"
            autofocus={true}
            required={true}
            state={this.nameInputValid}
            value={this.nameInput}
            on={{ input: this.setName }}
            placeholder="eg, Daily Timer"
          />
          <b-form-invalid-feedback state={this.nameInputValid}>Name must not be empty</b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          class="padding-bottom--normal-small margin-bottom--normal-small"
          description="Please specify a description for future reference."
        >
          <label class="d-block">Description:</label>
          <b-form-textarea
            size="sm"
            required={true}
            state={this.descriptionInputValid}
            value={this.descriptionInput}
            on={{ input: this.setDescription }}
            placeholder="eg, This block will fire every day (24 hours) and should be used for jobs that run daily."
          />
          <b-form-invalid-feedback state={this.descriptionInputValid}>
            Description must not be empty
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group
          class="padding-bottom--normal-small margin-bottom--normal-small"
          description={publishDisabled ? alreadyPublishedText : newPublishText}
        >
          <b-form-checkbox
            class="mr-sm-2 mb-sm-0"
            disabled={publishDisabled}
            on={{
              change: () => this.setPublishStatus(!this.publishStatus)
            }}
            checked={this.publishStatus}
          >
            {publishDisabled
              ? 'This block has already been publicly published.'
              : 'Publish to the Refinery Block Repository?'}
          </b-form-checkbox>
        </b-form-group>
        <div class="text-align--center">
          <b-button variant="primary" class="col-lg-8 mt-3" type="submit">
            {hasExistingBlock ? 'Update' : 'Publish'} Saved Block
          </b-button>
        </div>
      </b-form>
    );
  }

  renderModal() {
    if (!this.setModalVisibility) {
      throw new Error('Invalid modal configuration');
    }

    const setModalVisibility = this.setModalVisibility;

    const modalOnHandlers = {
      hidden: () => setModalVisibility(false)
    };

    return (
      <b-modal
        on={modalOnHandlers}
        hide-footer={true}
        title={this.existingBlockMetadata ? editModeTitle : addModeTitle}
        visible={this.modalVisibility}
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
