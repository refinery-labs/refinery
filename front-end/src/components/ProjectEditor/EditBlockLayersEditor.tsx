import Component from 'vue-class-component';
import Vue from 'vue';
import { Prop } from 'vue-property-decorator';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { arnRegex } from '@/constants/project-editor-constants';
import { nopWrite } from '@/utils/block-utils';
import { BlockLocalCodeSyncStoreModule } from '@/store';
import { EditorProps } from '@/types/component-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';

export interface BlockLayersEditorProps {
  readOnly: boolean;

  activeBlockId: string | null;
  activeBlockName: string | null;
  layers: string[];
  container: string;

  canAddMoreLayers: boolean;

  updateContainer: (container: string) => void;

  addNewLayer: () => void;
  deleteLayer: (index: number) => void;
  closeEditor: (discard: boolean) => void;

  updateLayer: (index: number, value: string) => void;

  modalMode?: boolean;
  isModalVisible?: boolean;
  onModalHidden?: () => void;
}

@Component
export class EditBlockLayersEditor extends Vue implements BlockLayersEditorProps {
  @Prop({ required: true }) activeBlockId!: string | null;
  @Prop({ required: true }) activeBlockName!: string | null;
  @Prop({ required: true }) layers!: string[];
  @Prop({ required: true }) container!: string;

  @Prop({ required: true }) readOnly!: boolean;

  @Prop({ required: true }) canAddMoreLayers!: boolean;

  @Prop({ required: true }) updateContainer!: (container: string) => void;

  @Prop({ required: true }) addNewLayer!: () => void;
  @Prop({ required: true }) deleteLayer!: (index: number) => void;
  @Prop({ required: true }) closeEditor!: (discard: boolean) => void;

  @Prop({ required: true }) updateLayer!: (index: number, value: string) => void;

  @Prop({ default: false }) modalMode!: boolean;
  @Prop({ default: false }) isModalVisible!: boolean;
  @Prop() onModalHidden?: () => void;

  public renderLayer(index: number, value: string) {
    const nameInputId = `layer-${index}-input-name`;

    const validArn = value !== '' ? arnRegex.test(value) : null;

    return (
      <div class="mb-2 mr-2 ml-2">
        <label for={nameInputId}>ARN for Layer #{index + 1}</label>
        <div class="display--flex">
          <b-input
            id={nameInputId}
            disabled={this.readOnly}
            class="col-md-10"
            placeholder="eg, arn:aws:lambda:us-west-2:123456789012:layer:my-layer:3"
            state={validArn}
            value={value}
            required={true}
            on={{ update: (val: string) => this.updateLayer(index, val) }}
          />
          <div class="width--100percent ml-2">
            <b-button
              class="width--100percent"
              disabled={this.readOnly}
              variant="danger"
              on={{ click: () => this.deleteLayer(index) }}
            >
              <span class="fas fa-trash" />
            </b-button>
          </div>
        </div>
        <b-form-invalid-feedback state={validArn}>
          You must provide a valid ARN for the layer. For some example Layer ARNs, refer to this{' '}
          <a href="https://github.com/mthenw/awesome-layers" target="_blank">
            repository
          </a>
          .
          <br />
          Note: The region must be "us-west-2". You can manually change the region in the ARN to this. Layers are
          published globally and setting "us-west-2" will just work.
        </b-form-invalid-feedback>
      </div>
    );
  }

  public renderContents() {
    const helperText = (
      <div class="text-align--center padding-top--big padding-bottom--big">
        <h4>
          You currently do not have any block layers set. To get started adding a new block layer, click the button
          above.
          <br />
          {/*For more information on what block layers are used for, please see the documentation here.*/}
        </h4>
      </div>
    );

    const arnsValid = this.layers.some(layer => !arnRegex.test(layer));

    return (
      <b-form>
        <b-form-group
          class="margin-bottom--none padding-bottom--small"
          description="These are standard AWS Lambda layers, which may be used to add functionality to the environment your Lambda runs in."
        >
          <div class="background--content border--content padding-top--normal">
            {this.layers.map((value, index) => this.renderLayer(index, value))}
            {this.layers.length === 0 ? helperText : null}
          </div>
        </b-form-group>
      </b-form>
    );
  }

  public renderContainerEditor() {
    const editorProps: EditorProps = {
      name: `docker-container`,
      lang: 'text',
      content: this.container,
      onChange: this.updateContainer
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  public renderModal() {
    const nameString = `${this.readOnly ? 'View' : 'Edit'} Environment for '${this.activeBlockName}'`;

    const addNewLayerButton = (
      <b-button variant="primary" on={{ click: this.addNewLayer }} disabled={!this.canAddMoreLayers}>
        Add New Block Layer
      </b-button>
    );

    const modalOnHandlers = {
      hidden: this.onModalHidden
    };

    const bottomStateButtons = (
      <div class="display--flex justify-content-end margin-between-sides--normal mt-2">
        <b-button variant="outline-danger" on={{ click: () => this.closeEditor(true) }}>
          Reset Changes
        </b-button>
        <b-button variant="primary" on={{ click: () => this.closeEditor(false) }}>
          Save Changes
        </b-button>
      </div>
    );

    return (
      <b-modal
        ref={`code-modal-${this.activeBlockId}`}
        on={modalOnHandlers}
        hide-footer={true}
        no-close-on-esc={true}
        size="xl"
        title={nameString}
        visible={this.isModalVisible}
      >
        <div>
          <b-tabs class="mt-3">
            <b-tab title="Lambda Layers">
              <div class="display--flex justify-content-end mb-2">{this.readOnly ? null : addNewLayerButton}</div>
              {this.renderContents()}
            </b-tab>
            <b-tab title="Docker Container">{this.renderContainerEditor()}</b-tab>
          </b-tabs>
          {this.readOnly ? null : bottomStateButtons}
        </div>
      </b-modal>
    );
  }

  public render() {
    if (this.modalMode && this.modalMode) {
      return this.renderModal();
    }

    return (
      <div>
        {this.renderContents()}
        <b-button>Close</b-button>
      </div>
    );
  }
}
