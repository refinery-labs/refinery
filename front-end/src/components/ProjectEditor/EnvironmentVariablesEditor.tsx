import Component from 'vue-class-component';
import Vue from 'vue';
import { Prop } from 'vue-property-decorator';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { EnvVariableRow } from '@/store/modules/panes/environment-variables-editor';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps } from '@/types/component-types';
import { SupportedLanguage } from '@/types/graph';

export interface EnvironmentVariablesEditorProps {
  readOnly: boolean;

  activeBlockId: string | null;
  activeBlockName: string | null;
  envVariableList: EnvVariableRow[];

  addNewVariable: () => void;
  deleteVariable: (id: string) => void;
  closeEditor: (discard: boolean) => void;

  setVariableName: (id: string, name: string) => void;
  setVariableValue: (id: string, value: string) => void;
  setVariableRequired: (id: string, required: boolean) => void;
  setVariableDescription: (id: string, description: string) => void;

  modalMode?: boolean;
  isModalVisible?: boolean;
  onModalHidden?: () => void;
}

@Component
export class EnvironmentVariablesEditor extends Vue implements EnvironmentVariablesEditorProps {
  @Prop({ required: true }) activeBlockId!: string | null;
  @Prop({ required: true }) activeBlockName!: string | null;
  @Prop({ required: true }) envVariableList!: EnvVariableRow[];

  @Prop({ required: true }) readOnly!: boolean;

  @Prop({ required: true }) addNewVariable!: () => void;
  @Prop({ required: true }) deleteVariable!: (id: string) => void;
  @Prop({ required: true }) closeEditor!: (discard: boolean) => void;

  @Prop({ required: true }) setVariableName!: (id: string, name: string) => void;
  @Prop({ required: true }) setVariableValue!: (id: string, value: string) => void;
  @Prop({ required: true }) setVariableRequired!: (id: string, required: boolean) => void;
  @Prop({ required: true }) setVariableDescription!: (id: string, description: string) => void;

  @Prop({ default: false }) modalMode!: boolean;
  @Prop({ default: false }) isModalVisible!: boolean;
  @Prop() onModalHidden?: () => void;

  public renderEnvVariableRow(params: EnvVariableRow) {
    const { id, value, name, description, required, valid } = params;

    const nameInputId = `env-variable-${id}-input-name`;
    const valueInputId = `env-variable-${id}-input-value`;

    const deleteButton = (
      <button
        type="button"
        data-dismiss="modal"
        aria-label="Close"
        class="close environment-variable__delete"
        on={{ click: () => this.deleteVariable(id) }}
      >
        <span aria-hidden="true">×</span>
      </button>
    );

    const editorProps: EditorProps = {
      name: name,
      content: value !== null && value !== undefined ? value : '',
      readOnly: this.readOnly,
      lang: 'text',
      onChange: (value: string) => this.setVariableValue(id, value)
    };

    return (
      <div class="col-12 environment-variable__card">
        <b-card class="card-default">
          {this.readOnly ? null : deleteButton}
          <b-form on={{ submit: preventDefaultWrapper(() => {}) }}>
            <label for={nameInputId}>Name</label>
            <b-input
              id={nameInputId}
              disabled={this.readOnly}
              class="mb-2 mr-sm-2 mb-sm-0"
              placeholder="eg, EndpointPath"
              state={valid}
              value={name}
              on={{ change: (name: string) => this.setVariableName(id, name) }}
            />
            <b-form-invalid-feedback state={valid}>
              Invalid name for variable. Please review reserved variables names{' '}
              <a
                href="https://docs.aws.amazon.com/lambda/latest/dg/lambda-environment-variables.html"
                target="_blank"
                rel="noopener noreferrer"
              >
                here
              </a>
              .
            </b-form-invalid-feedback>

            <label class="mr-sm-2 mt-2" for={valueInputId}>
              Description
            </label>
            <b-input-group class="mb-2 mr-sm-2 mb-sm-0">
              <b-input
                id={valueInputId}
                disabled={this.readOnly}
                placeholder="eg, Path to the Get Foo Bar endpoint"
                value={description}
                on={{ change: (description: string) => this.setVariableDescription(id, description) }}
              />
            </b-input-group>

            <label class="mr-sm-2 mt-2" for={valueInputId}>
              Value
            </label>
            <b-input-group class="mb-2 mb-sm-0">
              <RefineryCodeEditor props={editorProps} />
            </b-input-group>

            <b-form-checkbox
              class="mr-sm-2 mb-sm-0"
              disabled={this.readOnly}
              on={{ change: () => this.setVariableRequired(id, !required) }}
              checked={required}
            >
              Required
            </b-form-checkbox>
          </b-form>
        </b-card>
      </div>
    );
  }

  public renderContents() {
    const helperText = (
      <div class="text-align--center padding-top--big padding-bottom--big">
        <h4>
          You currently do not have any block environment variables defined. To get started adding a new environment
          variable, click the button above.
          <br />
          {/*For more information on what block settings are used for, please see the documentation here.*/}
        </h4>
      </div>
    );

    const contentsClasses = {
      'environment-variable-cards-container': true,
      'container border-divider--all background--content': true,
      'mt-2 mb-2 padding--big padding-bottom--normal': true,
      'overflow--scroll-y-auto overflow--hidden-x': true
    };

    return (
      <div class={contentsClasses}>
        <div class="environment-variable__card-group display--flex flex-wrap">
          {this.envVariableList.map(this.renderEnvVariableRow)}
        </div>
        {this.envVariableList.length === 0 ? helperText : null}
      </div>
    );
  }

  public renderModal() {
    const nameString = `${this.readOnly ? 'View' : 'Edit'} Block Environment Variables for '${this.activeBlockName}'`;

    const addNewVariableButton = (
      <b-button variant="primary" on={{ click: this.addNewVariable }}>
        Add New Environment Variable
      </b-button>
    );

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

    const modalOnHandlers = {
      hidden: this.onModalHidden
    };

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
        <div class="display--flex justify-content-end mb-2">
          <div class="flex-grow--1 text-align--left padding-top--normal-small">
            <label class="mb-0">Block Environment Variables:</label>
          </div>
          {this.readOnly ? null : addNewVariableButton}
        </div>
        {this.renderContents()}

        {this.readOnly ? null : bottomStateButtons}
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
