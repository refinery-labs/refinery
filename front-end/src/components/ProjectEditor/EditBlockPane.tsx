import Vue, { CreateElement, VNode, VueConstructor } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import AceEditor from '@/components/Common/AceEditor.vue';
import { Prop } from 'vue-property-decorator';
import {
  LambdaWorkflowState,
  ScheduleTriggerWorkflowState,
  SnsTopicWorkflowState,
  SupportedLanguage,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';

const editBlock = namespace('project/editBlockPane');

const blockNameText = 'Name of the block.';
const returnDataText = 'Data returned from the Lambda.';
const languagesText = 'Language of code block.';
const importLibsText = 'Dependencies for the code.';
const codeEditorText = 'Code to be executed by the block.';
const maxExecutionTimeText = 'Maximum time the code may execute before being killed in seconds.';
const maxExecutionMemoryText = 'Maximum memory for the code to use during execution.';
// TODO: Add support for Layers
// const layersText = <span>
//   The ARN(s) of the
//   <a href="https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html" target="_blank">layers</a> you
//   wish to use with this Lambda. There is a hard AWS limit of five layers per Lambda.
// </span>;

@Component
export class BlockScheduleExpressionInput extends Vue {
  @editBlock.State selectedNode!: ScheduleTriggerWorkflowState | null;
  @editBlock.Mutation setScheduleExpression!: (name: string) => void;

  public render() {
    if (!this.selectedNode) {
      return null;
    }

    const selectedNode = this.selectedNode;

    return (
      <b-form-group id={`block-name-group-${selectedNode.id}`}>
        <label class="d-block" htmlFor={`block-name-${selectedNode.id}`}>
          Schedule Expression:
        </label>
        <div class="input-group with-focus">
          <b-form-input
            id={`block-schedule-expression-${selectedNode.id}`}
            type="text"
            required
            value={selectedNode.schedule_expression}
            on={{ input: this.setScheduleExpression }}
            placeholder="cron(15 10 * * ? *)"
          />
        </div>
        <small class="form-text text-muted">
          <a
            href="https://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html"
            target="_blank"
          >
            Schedule expression
          </a>{' '}
          indicating how often the attached blocks should be run.
        </small>
      </b-form-group>
    );
  }
}

@Component
export class BlockNameInput extends Vue {
  @editBlock.State selectedNode!: WorkflowState | null;
  @editBlock.Mutation setBlockName!: (name: string) => void;

  public render() {
    if (!this.selectedNode) {
      return null;
    }

    const selectedNode = this.selectedNode;

    return (
      <b-form-group id={`block-name-group-${selectedNode.id}`} description={blockNameText}>
        <label class="d-block" htmlFor={`block-name-${selectedNode.id}`}>
          Block Name:
        </label>
        <div class="input-group with-focus">
          <b-form-input
            id={`block-name-${selectedNode.id}`}
            type="text"
            required
            value={selectedNode.name}
            on={{ input: this.setBlockName }}
            placeholder="My Amazing Block"
          />
        </div>
      </b-form-group>
    );
  }
}

export interface FormProps {
  [index: string]: any;

  idPrefix: string;
  description: string;
  placeholder: string;
  name: string;
  type?: string;
  value: any;
  on: { change: Function };
}

export type LanguageToAceLang = { [key in SupportedLanguage]: string };

export const languageToAceLangMap: LanguageToAceLang = {
  [SupportedLanguage.NODEJS_8]: 'javascript',
  [SupportedLanguage.PYTHON_2]: 'python',
  [SupportedLanguage.GO1_12]: 'golang',
  [SupportedLanguage.PHP7]: 'php'
};

@Component
export class EditTopicBlock extends Vue {
  @Prop() selectedNode!: SnsTopicWorkflowState;

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockNameInput />
      </div>
    );
  }
}

@Component
export class EditScheduleTriggerBlock extends Vue {
  @Prop() selectedNode!: ScheduleTriggerWorkflowState;

  @editBlock.State wideMode!: boolean;

  @editBlock.Mutation setInputData!: (input_data: string) => void;
  @editBlock.Mutation setWidePanel!: (wide: boolean) => void;

  public renderCodeEditor(id: string) {
    const editorProps = {
      'editor-id': `editor-${this.selectedNode.id}-${id}`,
      lang: 'text',
      theme: 'monokai',
      content: this.selectedNode.input_string,
      on: { 'change-content': this.setInputData }
    };

    return (
      // @ts-ignore
      <AceEditor
        editor-id={editorProps['editor-id']}
        lang={editorProps.lang}
        theme="monokai"
        content={editorProps.content}
        on={editorProps.on}
      />
    );
  }

  public renderCodeEditorContainer() {
    const selectedNode = this.selectedNode;
    const expandOnClick = { click: () => this.setWidePanel(!this.wideMode) };

    return (
      <b-form-group
        id={`code-editor-group-${selectedNode.id}`}
        description="Some data to be passed to the connected Code Blocks as input."
      >
        <div class="display--flex">
          <label class="d-block flex-grow--1" htmlFor={`code-editor-${selectedNode.id}`}>
            Edit Return Data:
          </label>
          <b-button on={expandOnClick} class="edit-block-container__expand-button">
            <span class="fa fa-angle-double-left" />
          </b-button>
        </div>
        <div class="input-group with-focus edit-block-container__code-editor">{this.renderCodeEditor('pane')}</div>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockNameInput />
        <BlockScheduleExpressionInput />
        {this.renderCodeEditorContainer()}
      </div>
    );
  }
}

@Component
export class EditLambdaBlock extends Vue {
  @Prop() selectedNode!: LambdaWorkflowState;

  @editBlock.State showCodeModal!: boolean;
  @editBlock.State wideMode!: boolean;

  @editBlock.Mutation setCodeModalVisibility!: (visible: boolean) => void;
  @editBlock.Mutation setWidePanel!: (wide: boolean) => void;

  @editBlock.Mutation setCodeInput!: (code: string) => void;
  @editBlock.Mutation setCodeLanguage!: (lang: SupportedLanguage) => void;
  @editBlock.Mutation setDependencyImports!: (libraries: string[]) => void;
  @editBlock.Mutation setMaxExecutionTime!: (maxExecTime: number) => void;
  @editBlock.Mutation setExecutionMemory!: (memory: number) => void;
  @editBlock.Mutation setLayers!: (layers: string[]) => void;

  public renderCodeEditorModal() {
    const nameString = `Edit Code for '${this.selectedNode.name}'`;

    const modalOnHandlers = {
      hidden: () => this.setCodeModalVisibility(false)
    };

    return (
      <b-modal
        ref={`code-modal-${this.selectedNode.id}`}
        on={modalOnHandlers}
        ok-only
        size="xl"
        title={nameString}
        visible={this.showCodeModal}
      >
        <div class="d-block text-center display--flex code-modal-editor-container">
          <div class="height--100percent width--100percent flex-grow--1">{this.renderCodeEditor('modal')}</div>
        </div>
      </b-modal>
    );
  }

  public renderCodeEditor(id: string) {
    const editorProps = {
      'editor-id': `editor-${this.selectedNode.id}-${id}`,
      lang: languageToAceLangMap[this.selectedNode.language],
      theme: 'monokai',
      content: this.selectedNode.code,
      on: { 'change-content': this.setCodeInput }
    };

    return (
      // @ts-ignore
      <AceEditor
        editor-id={editorProps['editor-id']}
        lang={editorProps.lang}
        theme="monokai"
        content={editorProps.content}
        on={editorProps.on}
      />
    );
  }

  public renderCodeEditorContainer() {
    const selectedNode = this.selectedNode;

    const expandOnClick = { click: () => this.setWidePanel(!this.wideMode) };
    const fullscreenOnClick = {
      click: () => this.setCodeModalVisibility(true)
    };

    return (
      <b-form-group id={`code-editor-group-${selectedNode.id}`} description={codeEditorText}>
        <div class="display--flex">
          <label class="d-block flex-grow--1" htmlFor={`code-editor-${selectedNode.id}`}>
            Edit Block Code:
          </label>
          <b-button on={fullscreenOnClick} class="edit-block-container__expand-button">
            <span class="fa fa-expand" />
          </b-button>
          <b-button on={expandOnClick} class="edit-block-container__expand-button">
            <span class="fa fa-angle-double-left" />
          </b-button>
        </div>
        <div class="input-group with-focus edit-block-container__code-editor">{this.renderCodeEditor('pane')}</div>
      </b-form-group>
    );
  }

  public renderForm(selectedNode: WorkflowState, inputProps: FormProps) {
    const { idPrefix, name, description, type } = inputProps;

    return (
      <b-form-group id={`${idPrefix}-group-${selectedNode.id}`} description={description}>
        <label class="d-block" htmlFor={`${idPrefix}-${selectedNode.id}`}>
          {name}:
        </label>
        <div class="input-group with-focus">
          <b-form-input
            id={`${idPrefix}-${selectedNode.id}`}
            type={type || 'text'}
            required
            max={inputProps.max}
            min={inputProps.min}
            step={inputProps.step}
            value={inputProps.value}
            {...inputProps}
          />
        </div>
      </b-form-group>
    );
  }

  public renderLanguageSelector() {
    const selectedNode = this.selectedNode;
    return (
      <b-form-group id={`block-language-group-${selectedNode.id}`} description={languagesText}>
        <label class="d-block" htmlFor={`block-language-${selectedNode.id}`}>
          Block Runtime:
        </label>
        <div class="input-group with-focus">
          <b-form-select
            id={`block-language-${selectedNode.id}`}
            value={this.selectedNode.language}
            on={{ input: this.setCodeLanguage }}
            options={Object.values(SupportedLanguage)}
          />
        </div>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    const maxExecutionTimeProps: FormProps = {
      idPrefix: 'max-execution',
      description: maxExecutionTimeText,
      name: 'Max Execution Time (seconds)',
      placeholder: '30',
      min: 15,
      max: 60 * 15,
      step: 15,

      type: 'number',
      value: this.selectedNode.max_execution_time.toString(),
      on: { change: this.setMaxExecutionTime }
    };

    const maxMemoryProps: FormProps = {
      idPrefix: 'max-memory',
      description: maxExecutionMemoryText,
      name: 'Instance Max Memory Size (MBs)',
      placeholder: '768',
      type: 'number',
      number: true,
      max: 3072,
      min: 128,
      step: 64,
      value: this.selectedNode.memory.toString(),
      on: { change: this.setExecutionMemory }
    };

    return (
      <div>
        <BlockNameInput />
        {this.renderLanguageSelector()}
        {this.renderCodeEditorContainer()}
        {this.renderForm(this.selectedNode, maxExecutionTimeProps)}
        {this.renderForm(this.selectedNode, maxMemoryProps)}
        <b-button variant="dark" class="col-12 mb-3">
          Edit Environment Variables
        </b-button>
        <b-button variant="outline-danger" class="col-12 mb-3">
          Delete Block
        </b-button>

        {this.renderCodeEditorModal()}
      </div>
    );
  }
}

export type BlockTypeToEditorComponent = { [key in WorkflowStateType]: VueConstructor };

export const blockTypeToEditorComponentLookup: BlockTypeToEditorComponent = {
  [WorkflowStateType.LAMBDA]: EditLambdaBlock,
  [WorkflowStateType.SNS_TOPIC]: EditTopicBlock,
  [WorkflowStateType.SCHEDULE_TRIGGER]: EditScheduleTriggerBlock,
  [WorkflowStateType.API_ENDPOINT]: EditLambdaBlock,
  [WorkflowStateType.API_GATEWAY]: EditLambdaBlock,
  [WorkflowStateType.API_GATEWAY_RESPONSE]: EditLambdaBlock,
  [WorkflowStateType.SQS_QUEUE]: EditLambdaBlock
};

@Component
export default class EditBlockPane extends Vue {
  @editBlock.State selectedNode!: WorkflowState | null;
  @editBlock.State confirmDiscardModalVisibility!: boolean;
  @editBlock.State isStateDirty!: boolean;
  @editBlock.State wideMode!: boolean;

  @editBlock.Mutation setConfirmDiscardModalVisibility!: (visibility: boolean) => void;

  @editBlock.Action cancelAndResetBlock!: () => void;
  @editBlock.Action tryToCloseBlock!: () => void;
  @editBlock.Action saveBlock!: () => void;

  public saveBlockClicked(e: Event) {
    e.preventDefault();
    this.saveBlock();
  }

  public renderConfirmDiscardModal() {
    if (!this.selectedNode) {
      return;
    }

    const nameString = `Are you sure you want to discard changes to '${this.selectedNode.name}'?`;

    const modalOnHandlers = {
      hidden: () => this.setConfirmDiscardModalVisibility(false),
      ok: () => this.cancelAndResetBlock()
    };

    return (
      <b-modal
        ref={`confirm-discard-${this.selectedNode.id}`}
        on={modalOnHandlers}
        ok-variant="danger"
        footer-class="p-2"
        title={nameString}
        visible={this.confirmDiscardModalVisibility}
      >
        You will lose any changes made to the block!
      </b-modal>
    );
  }

  public renderContentWrapper() {
    if (!this.selectedNode) {
      return <div />;
    }

    const ActiveEditorComponent = blockTypeToEditorComponentLookup[this.selectedNode.type];

    const props = { selectedNode: this.selectedNode as Object };

    const formClasses = {
      'mb-3 mt-3 text-align--left': true,
      'edit-block-container__form--normal': !this.wideMode,
      'edit-block-container__form--wide': this.wideMode
    };

    return (
      <b-form class={formClasses} on={{ submit: this.saveBlockClicked }}>
        <div class="edit-block-container__scrollable overflow--scroll-y-auto">
          <ActiveEditorComponent props={props} />
        </div>
        <div class="row edit-block-container__bottom-buttons">
          <b-button-group class="col-12">
            <b-button variant="secondary" class="col-6" on={{ click: this.tryToCloseBlock }}>
              {this.isStateDirty ? 'Cancel' : 'Close'}
            </b-button>
            <b-button variant="primary" class="col-6" type="submit" disabled={!this.isStateDirty}>
              Save Block
            </b-button>
          </b-button-group>
        </div>
      </b-form>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <b-container class="edit-block-container">
        {this.renderContentWrapper()}
        {this.renderConfirmDiscardModal()}
      </b-container>
    );
  }
}
