import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import VueMarkdown from 'vue-markdown';
import Loading from '@/components/Common/Loading.vue';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { CreateSavedBlockViewProps, EditorProps, LoadingContainerProps } from '@/types/component-types';
import { SavedBlockStatusCheckResult, SharedBlockPublishStatus } from '@/types/api-types';
import {
  addModeTitle,
  alreadyPublishedText,
  editModeTitle,
  inputDataExample,
  newPublishText
} from '@/constants/saved-block-constants';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { SupportedLanguage } from '@/types/graph';

@Component({
  components: {
    'vue-markdown': VueMarkdown
  }
})
export default class CreateSavedBlockView extends Vue implements CreateSavedBlockViewProps {
  @Prop({ required: true }) public modalMode!: boolean;

  @Prop({ required: true }) descriptionInput!: string | null;
  @Prop({ required: true }) existingBlockMetadata!: SavedBlockStatusCheckResult | null;
  @Prop({ required: true }) descriptionInputValid!: boolean;
  @Prop({ required: true }) nameInput!: string | null;
  @Prop({ required: true }) nameInputValid!: boolean;
  @Prop({ required: true }) savedDataInput!: string | null;
  @Prop({ required: true }) isBusyPublishing!: boolean;
  @Prop({ required: true }) publishStatus!: boolean;

  @Prop({ required: true }) publishBlock!: () => void;
  @Prop({ required: true }) setDescription!: (s: string) => void;
  @Prop({ required: true }) setName!: (s: string) => void;
  @Prop({ required: true }) setSavedDataInput!: (s: string) => void;
  @Prop({ required: true }) setPublishStatus!: (s: boolean) => void;

  @Prop() modalVisibility?: boolean;
  @Prop() setModalVisibility?: (b: boolean) => void;

  getPublishDisabled() {
    if (!this.existingBlockMetadata) {
      return false;
    }

    return this.existingBlockMetadata.share_status === SharedBlockPublishStatus.PUBLISHED;
  }

  renderRenderedDescriptionMarkdown() {
    if (!this.descriptionInput) {
      return null;
    }

    return (
      <div>
        <label class="mt-2 d-block">Description Preview:</label>
        <vue-markdown html={false} source={this.descriptionInput} />
      </div>
    );
  }

  renderContents() {
    const hasExistingBlock = this.existingBlockMetadata !== null;
    const publishDisabled = this.getPublishDisabled();

    const loadingProps: LoadingContainerProps = {
      label: 'Publishing Saved Block...',
      show: this.isBusyPublishing
    };

    const description = [
      'Please specify a description for future reference. You may use ',
      <a href="https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet" target="_blank">
        Markdown
      </a>,
      ' for this field.'
    ];

    const editorProps: EditorProps = {
      name: `create-saved-block-data`,
      // Set Nodejs because it supports JSON
      lang: SupportedLanguage.NODEJS_8,
      content: this.savedDataInput || inputDataExample,
      onChange: this.setSavedDataInput
    };

    return (
      <Loading props={loadingProps}>
        <b-form on={{ submit: preventDefaultWrapper(this.publishBlock) }}>
          <b-form-group
            class="padding-bottom--normal-small margin-bottom--normal-small"
            description="This is the name that will be seen when viewing this block in the Saved Block viewer. Make this something helpful for yourself and others!"
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
          <b-form-group class="padding-bottom--normal-small margin-bottom--normal-small">
            <label class="d-block">Description:</label>
            <b-form-textarea
              size="sm"
              required={true}
              state={this.descriptionInputValid}
              value={this.descriptionInput}
              on={{ input: this.setDescription }}
              placeholder="eg, This block will fire every day (24 hours) and should be used for jobs that run daily."
            />
            <slot name="description">
              <small class="form-text text-muted">{description}</small>
            </slot>
            <b-form-invalid-feedback state={this.descriptionInputValid}>
              Description must not be empty
            </b-form-invalid-feedback>
            {this.renderRenderedDescriptionMarkdown()}
          </b-form-group>

          <b-form-group
            className="padding-bottom--normal-small margin-bottom--normal-small"
            description="This data will help your users understand how to use the block. Please fill out the schema with the data that your block will require."
          >
            <label class="d-block">Example Input Data:</label>
            <RefineryCodeEditor props={editorProps} />
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
      </Loading>
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
        size="xl max-width--600px"
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
