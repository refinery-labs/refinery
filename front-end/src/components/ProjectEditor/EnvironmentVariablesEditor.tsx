import Component from 'vue-class-component';
import Vue from 'vue';
import { Prop } from 'vue-property-decorator';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { EnvVariableRow } from '@/store/modules/panes/environment-variables-editor';

export interface EnvironmentVariablesEditorProps {
  readOnly: boolean;

  activeBlockId: string | null;
  activeBlockName: string | null;
  envVariableList: EnvVariableRow[];

  addNewVariable: () => void;
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
  @Prop({ required: true }) closeEditor!: (discard: boolean) => void;

  @Prop({ required: true }) setVariableName!: (id: string, name: string) => void;
  @Prop({ required: true }) setVariableValue!: (id: string, value: string) => void;
  @Prop({ required: true }) setVariableRequired!: (id: string, required: boolean) => void;
  @Prop({ required: true }) setVariableDescription!: (id: string, description: string) => void;

  @Prop({ default: false }) modalMode!: boolean;
  @Prop({ default: false }) isModalVisible!: boolean;
  @Prop() onModalHidden?: () => void;

  public renderEnvVariableRow(params: EnvVariableRow) {
    const { id, value, name, description, required } = params;

    const nameInputId = `env-variable-${id}-input-name`;
    const valueInputId = `env-variable-${id}-input-value`;

    return (
      <b-card class="card-default">
        <b-card-body>
          <b-form on={{ submit: preventDefaultWrapper(() => {}) }}>
            <label for={nameInputId}>Name</label>
            <b-input
              id={nameInputId}
              disabled={this.readOnly}
              class="mb-2 mr-sm-2 mb-sm-0"
              placeholder="eg, EndpointPath"
              value={name}
              on={{ change: (name: string) => this.setVariableName(id, name) }}
            />

            <label class="mr-sm-2" for={valueInputId}>
              Value
            </label>
            <b-input-group class="mb-2 mr-sm-2 mb-sm-0">
              <b-input
                id={valueInputId}
                disabled={this.readOnly}
                placeholder="eg, https://example.com/api/foobar"
                value={value}
                on={{ change: (value: string) => this.setVariableValue(id, value) }}
              />
            </b-input-group>

            <label class="mr-sm-2" for={valueInputId}>
              Description
            </label>
            <b-input-group className="mb-2 mr-sm-2 mb-sm-0">
              <b-input
                id={valueInputId}
                disabled={this.readOnly}
                placeholder="eg, Path to the Get Foo Bar endpoint"
                value={description}
                on={{ change: (description: string) => this.setVariableDescription(id, description) }}
              />
            </b-input-group>

            <b-form-checkbox
              class="mt-2 mr-sm-2 mb-sm-0"
              disabled={this.readOnly}
              on={{ change: () => this.setVariableRequired(id, !required) }}
              checked={required}
            >
              Required
            </b-form-checkbox>
          </b-form>
        </b-card-body>
      </b-card>
    );
  }

  public renderContents() {
    const helperText = (
      <div class="text-align--center padding-top--big padding-bottom--big">
        <h4>
          You currently do not have any block variables set. To get started adding a new variable, click the button
          below.
          <br />
          For more information on what block variables are used for, please see the documentation here.
        </h4>
      </div>
    );

    return (
      <div class="container border-divider--all background--content mt-2 mb-2 padding--big padding-bottom--normal">
        <div class="overflow--scroll-y-auto overflow--hidden-x">
          <b-card-group columns>{this.envVariableList.map(this.renderEnvVariableRow)}</b-card-group>
          {this.envVariableList.length === 0 ? helperText : null}
        </div>
      </div>
    );
  }

  public renderModal() {
    const nameString = `${this.readOnly ? 'View' : 'Edit'} Block Variables for '${this.activeBlockName}'`;

    const modalOnHandlers = {
      hidden: this.onModalHidden
    };

    return (
      <b-modal
        ref={`code-modal-${this.activeBlockId}`}
        on={modalOnHandlers}
        hide-footer={true}
        size="xl"
        title={nameString}
        visible={this.isModalVisible}
      >
        <div class="display--flex justify-content-end mb-2">
          <div class="flex-grow--1 text-align--left padding-top--normal-small">
            <label class="mb-0">Block Variables:</label>
          </div>
          <b-button variant="primary" on={{ click: this.addNewVariable }}>
            Add New Variable
          </b-button>
        </div>
        {this.renderContents()}

        <div class="display--flex justify-content-end margin-between-sides--normal mt-2">
          <b-button variant="outline-danger" on={{ click: () => this.closeEditor(true) }}>
            Reset Changes
          </b-button>
          <b-button variant="primary" on={{ click: () => this.closeEditor(false) }}>
            Save Changes
          </b-button>
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
