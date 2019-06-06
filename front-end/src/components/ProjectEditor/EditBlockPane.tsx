import Vue, {CreateElement, VNode, VueConstructor} from 'vue';
import Component from 'vue-class-component';
import {namespace} from 'vuex-class';
import AceEditor from '@/components/Common/AceEditor.vue';
import {Prop} from 'vue-property-decorator';
import {LambdaWorkflowState, SupportedLanguage, WorkflowState, WorkflowStateType} from '@/types/graph';

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

function renderBlockNameInput(h: CreateElement, selectedNode: WorkflowState) {
  return (
    <b-form-group
      id={`block-name-group-${selectedNode.id}`}
      description={blockNameText}>
      <label class="d-block" htmlFor={`block-name-${selectedNode.id}`}>
        Block Name:
      </label>
      <div class="input-group with-focus">
        <b-form-input
          id={`block-name-${selectedNode.id}`}
          type="text"
          required
          value={selectedNode.name}
          placeholder="My Amazing Block" />
      </div>
    </b-form-group>
  );
}

@Component
export class CodeEditorBlock extends Vue {

}

export interface FormProps {
  [index: string]: any,
  idPrefix: string,
  description: string,
  placeholder: string,
  name: string,
  type?: string,
  value: any,
  on: {change: Function}
}

export type LanguageToAceLang = {
  [key in SupportedLanguage]: string
}

export const languageToAceLangMap: LanguageToAceLang = {
  [SupportedLanguage.NODEJS_8]: 'javascript',
  [SupportedLanguage.PYTHON_2]: 'python',
  [SupportedLanguage.GO1_12]: 'golang',
  [SupportedLanguage.PHP7]: 'php'
};

@Component
export class EditLambdaBlock extends Vue {
  @Prop() selectedNode!: LambdaWorkflowState;
  
  @editBlock.State showCodeModal!: boolean;
  
  @editBlock.Mutation setCodeModalVisibility!: (visible: boolean) => void;
  
  @editBlock.Mutation setBlockName!: (name: string) => void;
  
  @editBlock.Mutation setCodeInput!: (code: string) => void;
  @editBlock.Mutation setCodeLanguage!: (lang: SupportedLanguage) => void;
  @editBlock.Mutation setDependencyImports!: (libraries: string[]) => void;
  @editBlock.Mutation setMaxExecutionTime!: (maxExecTime: number) => void;
  @editBlock.Mutation setExecutionMemory!: (memory: number) => void;
  @editBlock.Mutation setLayers!: (layers: string[]) => void;
  
  public renderCodeEditorModal() {
    const nameString = `Edit Code for \'${this.selectedNode.name}\'`;
    
    const modalOnHandlers = {
      hidden: () => this.setCodeModalVisibility(false),
    };
    
    const buttonOnHandlers ={
      click: () => this.setCodeModalVisibility(false),
    };
    
    return (
      <b-modal ref={`code-modal-${this.selectedNode.id}`}
               on={modalOnHandlers}
               size="xl" title={nameString} visible={this.showCodeModal}>
        <div class="d-block text-center display--flex code-modal-editor-container">
          <h2>{nameString}</h2>
          <div class="height--100percent width--100percent flex-grow--1">
            {this.renderCodeEditor('modal')}
          </div>
        </div>
        <b-button class="mt-2" variant="primary" block on={buttonOnHandlers}>
          Close
        </b-button>
      </b-modal>
    );
  }
  
  public renderCodeEditor(id: string) {

    const editorProps = {
      'editor-id': `editor-${this.selectedNode.id}-${id}`,
      lang: languageToAceLangMap[this.selectedNode.language],
      theme: 'monokai',
      content: this.selectedNode.code,
      on: {'change-content': this.setCodeInput}
    };
    
    return (
      // @ts-ignore
      <AceEditor editor-id={editorProps['editor-id']} lang={editorProps.lang}
                 theme="monokai" content={editorProps.content} on={editorProps.on} />
    );
  }
  
  public renderCodeEditorContainer() {
    const buttonOnclick = {click: () => this.setCodeModalVisibility(true)};
    
    return (
      <div class="edit-block-container__code-editor">
        <b-button on={buttonOnclick} class="edit-block-container__expand-button">Expand</b-button>
        {this.renderCodeEditor('pane')}
      </div>
    );
  }
  
  public renderForm(selectedNode: WorkflowState, inputProps: FormProps) {
    const {idPrefix, name, description, type} = inputProps;
    
    return (
      <b-form-group
        id={`${idPrefix}-group-${selectedNode.id}`}
        description={description}>
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
            {...inputProps} />
        </div>
      </b-form-group>
    );
  }
  
  public renderLanguageSelector() {
    const selectedNode = this.selectedNode;
    return (
      <b-form-group
        id={`block-language-group-${selectedNode.id}`}
        description={languagesText}>
        <label class="d-block" htmlFor={`block-language-${selectedNode.id}`}>
          Block Runtime:
        </label>
        <div class="input-group with-focus">
          <b-form-select id={`block-language-${selectedNode.id}`}
                         value={this.selectedNode.language}
                         on={{change: this.setCodeLanguage}}
                         options={Object.values(SupportedLanguage)} />
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
      on:{change: this.setMaxExecutionTime}
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
      on:{change: this.setExecutionMemory}
    };
    
    return (
      <b-form class="mb-3 mt-3 text-align--left edit-block-container__form">
        <div class="edit-block-container__scrollable overflow--scroll-y-auto">
          {renderBlockNameInput(h, this.selectedNode)}
          {this.renderLanguageSelector()}
          {this.renderCodeEditorContainer()}
          {this.renderForm(this.selectedNode, maxExecutionTimeProps)}
          {this.renderForm(this.selectedNode, maxMemoryProps)}
          <b-button variant="dark" class="col-12 mb-3">Edit Environment Variables</b-button>
          <b-button variant="outline-danger" class="col-12 mb-3">Delete Block</b-button>
        </div>
        <div class="row edit-block-container__bottom-buttons">
          <b-button-group class="col-12">
            <b-button variant="secondary" class="col-6" type="reset">Cancel</b-button>
            <b-button variant="primary" class="col-6" type="submit">Save Block</b-button>
          </b-button-group>
        </div>
        {this.renderCodeEditorModal()}
      </b-form>
    );
  }
}

export type BlockTypeToEditorComponent = {
  [key in WorkflowStateType]: VueConstructor
}

export const blockTypeToEditorComponentLookup: BlockTypeToEditorComponent = {
  [WorkflowStateType.LAMBDA]: EditLambdaBlock,
  [WorkflowStateType.SNS_TOPIC]: EditLambdaBlock,
  [WorkflowStateType.SCHEDULE_TRIGGER]: EditLambdaBlock,
  [WorkflowStateType.API_ENDPOINT]: EditLambdaBlock,
  [WorkflowStateType.API_GATEWAY]: EditLambdaBlock,
  [WorkflowStateType.API_GATEWAY_RESPONSE]: EditLambdaBlock,
  [WorkflowStateType.SQS_QUEUE]: EditLambdaBlock
};

@Component
export default class EditBlockPane extends Vue {
  @editBlock.State selectedNode!: WorkflowState | null;
  
  public render(h: CreateElement): VNode {
    
    if (!this.selectedNode) {
      return <div />;
    }
    
    const ActiveEditorComponent = blockTypeToEditorComponentLookup[this.selectedNode.type];
    
    const props = {selectedNode: this.selectedNode as Object};
    
    return (
      <b-container class="edit-block-container">
        <ActiveEditorComponent props={props} />
      </b-container>
    );
  }
}
