import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import moment from 'moment';
import { blockTypeToImageLookup } from '@/constants/project-editor-constants';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { Prop } from 'vue-property-decorator';
import { ChosenBlock } from '@/types/add-block-types';
import { SharedBlockPublishStatus } from '@/types/api-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps, MarkdownProps } from '@/types/component-types';
import { BlockEnvironmentVariable, LambdaWorkflowState, WorkflowStateType } from '@/types/graph';
import RefineryMarkdown from '@/components/Common/RefineryMarkdown';
import { AddSavedBlockEnvironmentVariable } from '@/types/saved-blocks-types';

export interface ViewChosenSavedBlockPaneProps {
  chosenBlock: ChosenBlock;
  environmentVariables: AddSavedBlockEnvironmentVariable[] | null;

  addChosenBlock: () => void;
  goBackToAddBlockPane: () => void;

  setEnvironmentVariablesValue: (name: string, value: string) => void;
}

@Component
export default class ViewChosenSavedBlockPane extends Vue implements ViewChosenSavedBlockPaneProps {
  @Prop({ required: true }) chosenBlock!: ChosenBlock;
  @Prop({ required: true }) environmentVariables!: AddSavedBlockEnvironmentVariable[] | null;

  @Prop({ required: true }) addChosenBlock!: () => void;
  @Prop({ required: true }) goBackToAddBlockPane!: () => void;
  @Prop({ required: true }) setEnvironmentVariablesValue!: (name: string, value: string) => void;

  public renderBlockSelect() {
    const block = this.chosenBlock.block;

    const imagePath = blockTypeToImageLookup[block.type].path;
    const durationSinceUpdated = moment.duration(-moment().diff(block.timestamp * 1000)).humanize(true);

    const isPrivateBlock = this.chosenBlock.blockSource === 'private';
    const sharePillVariable = block.share_status === SharedBlockPublishStatus.PRIVATE ? 'success' : 'primary';
    const shareStatusText = isPrivateBlock && (
      <div class="text-muted text-align--center">
        <b-badge variant={sharePillVariable}>{block.share_status}</b-badge>
      </div>
    );

    const descriptionClasses = {
      'add-saved-block-container__description scrollable-pane-container': true,
      'padding-bottom--tiny padding-left--normal padding-top--normal padding-right--normal': true
    };

    const markdownProps: MarkdownProps = {
      content: block.description
    };

    return (
      <div class="width--100percent">
        <div class="display--flex flex-grow--1 width--100percent" style={{ 'min-width': '320px' }}>
          <div>
            <img class="add-block__image" src={imagePath} alt={block.name} />
            {shareStatusText}
          </div>
          <div class="flex-column align-items-start add-block__content">
            <div class="d-flex w-100 justify-content-between">
              <h4 class="mb-1">{block.name}</h4>
              <small>Published {durationSinceUpdated}</small>
            </div>
            <div class={descriptionClasses}>
              <h4 class="d-block">Block Description:</h4>
              <RefineryMarkdown props={markdownProps} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  renderSavedData() {
    if (this.chosenBlock.block.type !== WorkflowStateType.LAMBDA) {
      return null;
    }

    const block = this.chosenBlock.block.block_object as LambdaWorkflowState;

    // No saved data to display.
    if (block.saved_input_data === null || block.saved_input_data === undefined || block.saved_input_data === '') {
      return null;
    }

    const resultDataEditorProps: EditorProps = {
      name: `saved-block-input-data`,
      // This is very nice for rendering non-programming text
      lang: 'json',
      content: block.saved_input_data || '',
      wrapText: true,
      readOnly: true
    };

    return (
      <b-form-group class="mt-2 mb-0 padding-bottom--normal display--flex flex-direction--column">
        <div class="text-align--left run-lambda-container__text-label">
          <label class="text-light padding--none mt-0 mb-0 ml-2">Example Input Data:</label>
        </div>
        <div class="flex-grow--1">
          <div class="height--100percent position--relative">
            <RefineryCodeEditor props={resultDataEditorProps} />
          </div>
        </div>
      </b-form-group>
    );
  }

  renderEnvironmentVariables() {
    if (!this.environmentVariables) {
      return null;
    }

    const envVariableInputs = this.environmentVariables.map(env => (
      <b-form-group
        class="display--flex mb-1 padding-bottom--small"
        description={`Variable Description: ${env.description}`}
      >
        <label class="d-block mt-auto mb-auto">
          {env.name} ({`${env.required ? 'required' : 'optional'}`}):
        </label>
        <b-form-input
          class="flex-grow--1 mb-1"
          type="text"
          required={env.required}
          placeholder={`Description: ${env.description}`}
          state={env.valid}
          value={env.value}
          on={{ change: (s: string) => this.setEnvironmentVariablesValue(env.name, s) }}
        />
      </b-form-group>
    ));

    return (
      <b-form-group
        class="mt-2 mb-0 padding-bottom--normal"
        description="Block settings are passed as environment variables to the block. You must enter a value for any fields marked required before adding the block."
      >
        <label class="d-block">Block Settings (Environment Variables):</label>
        <div class="add-saved-block-container__environment-variables scrollable-pane-container padding--normal">
          {envVariableInputs}
        </div>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="text-align--left mb-2 ml-2 mr-2 add-saved-block-container">
        <a
          href=""
          class="mb-2 padding-bottom--normal mt-2 d-block"
          style="border-bottom: 1px dashed #eee;"
          on={{ click: preventDefaultWrapper(this.goBackToAddBlockPane) }}
        >
          {'<< Go Back'}
        </a>
        {this.renderBlockSelect()}
        {this.renderSavedData()}

        <b-form on={{ submit: preventDefaultWrapper(() => this.addChosenBlock()) }}>
          {this.renderEnvironmentVariables()}

          <b-button class="mt-2 width--100percent" variant="primary" type="submit">
            Add Block
          </b-button>
        </b-form>
      </div>
    );
  }
}
