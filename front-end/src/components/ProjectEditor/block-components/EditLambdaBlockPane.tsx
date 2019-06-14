import Component from 'vue-class-component';
import Vue, {CreateElement, VNode} from 'vue';
import {Prop} from 'vue-property-decorator';
import {LambdaWorkflowState, SupportedLanguage, WorkflowState} from '@/types/graph';
import {
  FormProps,
  languageToAceLangMap,
  LanguageToBaseRepoURLMap,
  LanguageToLibraryRepoURLMap
} from '@/types/project-editor-types';
import AceEditor from '@/components/Common/AceEditor.vue';
import {BlockNameInput} from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import {namespace} from 'vuex-class';
import {
  codeEditorText,
  languagesText,
  maxExecutionMemoryText,
  maxExecutionTimeText
} from '@/constants/project-editor-constants';
import {deepJSONCopy} from "@/lib/general-utils";

const editBlock = namespace('project/editBlockPane');

@Component
export class EditLambdaBlock extends Vue {
  @Prop() selectedNode!: LambdaWorkflowState;

  @editBlock.State showCodeModal!: boolean;
  @editBlock.State wideMode!: boolean;
  @editBlock.State librariesModalVisibility!: boolean;
  @editBlock.State enteredLibrary!: string;

  @editBlock.Mutation setCodeModalVisibility!: (visible: boolean) => void;
  @editBlock.Mutation setWidePanel!: (wide: boolean) => void;

  @editBlock.Mutation setLibrariesModalVisibility!: (visibility: boolean) => void;
  @editBlock.Mutation setCodeInput!: (code: string) => void;
  @editBlock.Mutation setCodeLanguage!: (lang: SupportedLanguage) => void;
  @editBlock.Mutation setDependencyImports!: (libraries: string[]) => void;
  @editBlock.Mutation setMaxExecutionTime!: (maxExecTime: number) => void;
  @editBlock.Mutation setExecutionMemory!: (memory: number) => void;
  @editBlock.Mutation setLayers!: (layers: string[]) => void;
  @editBlock.Mutation setEnteredLibrary!: (libraryName: string) => void;

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

  public changeCodeLanguage(language: SupportedLanguage) {
    // We need to reset the libraries
    // Otherwise you'll have npm libraries when you switch to Python :/
    this.setDependencyImports([]);
    this.setCodeLanguage(language);
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
            on={{input: this.changeCodeLanguage}}
            options={Object.values(SupportedLanguage)}
          />
        </div>
      </b-form-group>
    );
  }

  deleteLibrary(input: string) {
    const newLibrariesArray = this.selectedNode.libraries.filter(library => {
      return (library !== input);
    });
    this.setDependencyImports(newLibrariesArray);
  }

  addLibrary(e: Event) {
    e.preventDefault();
    const canonicalizedLibrary = this.enteredLibrary.trim();
    if (!this.selectedNode.libraries.includes(canonicalizedLibrary)) {
      const newLibrariesArray = deepJSONCopy(this.selectedNode.libraries).concat(canonicalizedLibrary);
      this.setDependencyImports(newLibrariesArray);
    }

    // Reset input
    this.setEnteredLibrary("");
  }

  public renderLibraryTable() {
    // If there are no currently-added libraries
    if (this.selectedNode.libraries.length === 0) {
      return (
        <div class="text-center">
          <i>You currently have no libraries! Add one below.</i>
          <br />
          <a href={LanguageToBaseRepoURLMap[this.selectedNode.language]} target="_blank">Click here to find a library for your Code Block.</a>
        </div>
      )
    }

    const libraryTable = this.selectedNode.libraries.map(library => {
        const packageRepoLink = LanguageToLibraryRepoURLMap[this.selectedNode.language] + encodeURIComponent(library);
        return (
          <b-list-group-item class="d-flex">
            <span class="float-left d-inline">
              <a href={packageRepoLink} target="_blank">{library}</a>
            </span>
            <div class="ml-auto float-right d-inline">
              <button type="button"
                      on={{click: this.deleteLibrary.bind(this, library)}}
                      class="btn btn-danger">
                <span class="fas fa-trash"></span>
              </button>
            </div>

          </b-list-group-item>
        );
      }
    );
    return (
      <b-list-group>
        {libraryTable}
      </b-list-group>
    );
  }

  public renderLibrariesModal() {
    if (!this.selectedNode) {
      return;
    }

    const modalOnHandlers = {
      hidden: () => this.setLibrariesModalVisibility(false),
      ok: () => this.setLibrariesModalVisibility(false),
    };

    return (
      <b-modal
        ref={`libraries-modal-${this.selectedNode.id}`}
        on={modalOnHandlers}
        ok-variant="primary"
        footer-class="p-2"
        title="Select the libraries for your Code Block"
        visible={this.librariesModalVisibility}
        ok-only
        ok-variant="secondary"
        ok-title="Close"
      >
        {this.renderLibraryTable()}

        <hr/>
        <b-form on={{submit: this.addLibrary}}>
          <b-form-group
            label="Library name:"
            label-for="library-input-field"
            description="The name of the library you want to install as a dependency."
          >
            <b-form-input
              id="library-input-field"
              type="text"
              required
              placeholder="Enter your library name"
              value={this.enteredLibrary}
              on={{input: this.setEnteredLibrary}}
            ></b-form-input>
          </b-form-group>
          <b-button type="submit" variant="primary">Add Library</b-button>
        </b-form>
      </b-modal>
    );
  }

  private viewLibraryModal() {
    // Reset library name input
    this.setEnteredLibrary("");
    this.setLibrariesModalVisibility(true);
  }

  public renderLibrarySelector() {
    // Go has no libraries, it's done via in-code imports
    if(this.selectedNode.language === SupportedLanguage.GO1_12) {
      return (
        <div></div>
      )
    }
    return (
      <b-form-group description="The libraries to install for your Block Code.">
        <label class="d-block">
          Block Imported Libraries:
        </label>
        <b-button variant="dark" class="col-12" on={{click: this.viewLibraryModal}}>
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
        {this.renderLibrariesModal()}
      </div>
    );
  }
}