import Component from 'vue-class-component';
import Vue, {CreateElement, VNode} from 'vue';
import {Prop} from 'vue-property-decorator';
import {LambdaWorkflowState, SupportedLanguage, WorkflowState} from '@/types/graph';
import {FormProps, languageToAceLangMap} from '@/types/project-editor-types';
import AceEditor from '@/components/Common/AceEditor.vue';
import {BlockNameInput} from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import {namespace} from 'vuex-class';
import {
  codeEditorText,
  languagesText,
  maxExecutionMemoryText,
  maxExecutionTimeText
} from '@/constants/project-editor-constants';

const editBlock = namespace('project/editBlockPane');

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
      'editor-id': `code-editor-${this.selectedNode.id}-${id}`,
      lang: languageToAceLangMap[this.selectedNode.language],
      theme: 'monokai',
      content: this.selectedNode.code,
      on: {'change-content': this.setCodeInput}
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

    const expandOnClick = {click: () => this.setWidePanel(!this.wideMode)};
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
            <span class="fa fa-expand"/>
          </b-button>
          <b-button on={expandOnClick} class="edit-block-container__expand-button">
            <span class="fa fa-angle-double-left"/>
          </b-button>
        </div>
        <div class="input-group with-focus edit-block-container__code-editor">{this.renderCodeEditor('pane')}</div>
      </b-form-group>
    );
  }

  public renderForm(selectedNode: WorkflowState, inputProps: FormProps) {
    const {idPrefix, name, description, type} = inputProps;

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
            on={{input: this.setCodeLanguage}}
            options={Object.values(SupportedLanguage)}
          />
        </div>
      </b-form-group>
    );
  }

  public renderLibrarySelector() {
    const selectedNode = this.selectedNode;
    return (
      <b-form-group description="The libraries to install for your Block Code.">
        <label class="d-block">
          Block Imported Libraries:
        </label>
        <b-button variant="dark" class="col-12">
          Modify Libraries (<i>{this.selectedNode.libraries.length.toString()} Imported</i>)
        </b-button>
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
      on: {change: this.setMaxExecutionTime}
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
      on: {change: this.setExecutionMemory}
    };

    return (
      <div>
        <BlockNameInput/>
        {this.renderLanguageSelector()}
        {this.renderLibrarySelector()}
        {this.renderCodeEditorContainer()}
        {this.renderForm(this.selectedNode, maxExecutionTimeProps)}
        {this.renderForm(this.selectedNode, maxMemoryProps)}
        <b-button variant="dark" class="col-12 mb-3">
          Edit Environment Variables
        </b-button>
        {this.renderCodeEditorModal()}
      </div>
    );
  }
}