import Component from 'vue-class-component';
import Vue, { VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { LambdaWorkflowState, SupportedLanguage, WorkflowState, WorkflowStateType } from '@/types/graph';
import { FormProps, LanguageToBaseRepoURLMap, LanguageToLibraryRepoURLMap } from '@/types/project-editor-types';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import { namespace } from 'vuex-class';
import {
  codeEditorText,
  languagesText,
  maxExecutionMemoryText,
  maxExecutionTimeText
} from '@/constants/project-editor-constants';
import { RunLambdaDisplayMode } from '@/components/RunLambda';
import RunEditorCodeBlockContainer from '@/components/ProjectEditor/RunEditorCodeBlockContainer';
import RunDeployedCodeBlockContainer from '@/components/DeploymentViewer/RunDeployedCodeBlockContainer';
import { nopWrite } from '@/utils/block-utils';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps } from '@/types/component-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { libraryBuildArguments, startLibraryBuild } from '@/store/fetchers/api-helpers';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { BlockDocumentationButton } from '@/components/ProjectEditor/block-components/EditBlockDocumentationButton';

const editBlock = namespace('project/editBlockPane');
const viewBlock = namespace('viewBlock');

@Component
export class EditLambdaBlock extends Vue {
  @Prop({ required: true }) selectedNode!: LambdaWorkflowState;
  @Prop({ required: true }) readOnly!: boolean;

  // State pulled from Deployment view.
  @viewBlock.State('showCodeModal') showCodeModalDeployment!: boolean;
  @viewBlock.State('wideMode') wideModeDeployment!: boolean;
  @viewBlock.State('librariesModalVisibility') librariesModalVisibilityDeployment!: boolean;

  @viewBlock.Getter getAwsConsoleUri!: string | null;
  @viewBlock.Getter getLambdaMonitorUri!: string | null;
  @viewBlock.Getter getLambdaCloudWatchUri!: string | null;

  @viewBlock.Mutation('setCodeModalVisibility') setCodeModalVisibilityDeployment!: (visible: boolean) => void;
  @viewBlock.Mutation('setWidePanel') setWidePanelDeployment!: (wide: boolean) => void;
  @viewBlock.Mutation('setLibrariesModalVisibility') setLibrariesModalVisibilityDeployment!: (
    visibility: boolean
  ) => void;
  @viewBlock.Action openAwsConsoleForBlock!: () => void;
  @viewBlock.Action openAwsMonitorForCodeBlock!: () => void;
  @viewBlock.Action openAwsCloudwatchForCodeBlock!: () => void;

  // State pulled from Project view
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
  @editBlock.Mutation deleteDependencyImport!: (libraryName: string) => void;
  @editBlock.Mutation addDependencyImport!: (libraryName: string) => void;

  public renderCodeEditorModal() {
    const nameString = `Edit Code for '${this.selectedNode.name}'`;

    const setCodeModalVisibility = this.readOnly ? this.setCodeModalVisibilityDeployment : this.setCodeModalVisibility;
    const showCodeModal = this.readOnly ? this.showCodeModalDeployment : this.showCodeModal;

    const RunLambdaContainer = this.readOnly ? RunDeployedCodeBlockContainer : RunEditorCodeBlockContainer;

    const modalOnHandlers = {
      hidden: () => setCodeModalVisibility(false)
    };

    return (
      <b-modal
        ref={`code-modal-${this.selectedNode.id}`}
        on={modalOnHandlers}
        hide-footer={true}
        size="xl no-max-width"
        title={nameString}
        visible={showCodeModal}
      >
        <div class="text-center display--flex flex-direction--column code-modal-editor-container overflow--scroll-y-auto overflow--hidden-x">
          <div class="width--100percent flex-grow--1 display--flex">{this.renderCodeEditor()}</div>
          <div class="width--100percent">
            <RunLambdaContainer props={{ displayMode: RunLambdaDisplayMode.fullscreen }} />
          </div>
        </div>
      </b-modal>
    );
  }

  public renderCodeEditor() {
    const setCodeInput = this.readOnly ? nopWrite : this.setCodeInput;

    const editorProps: EditorProps = {
      name: 'block-code',
      lang: this.selectedNode.language,
      readOnly: this.readOnly,
      content: this.selectedNode.code,
      onChange: setCodeInput
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  public renderCodeEditorContainer() {
    const selectedNode = this.selectedNode;

    const setWidePanel = this.readOnly ? this.setWidePanelDeployment : this.setWidePanel;
    const wideMode = this.readOnly ? this.wideModeDeployment : this.wideMode;
    const setCodeModalVisibility = this.readOnly ? this.setCodeModalVisibilityDeployment : this.setCodeModalVisibility;

    const expandOnClick = { click: () => setWidePanel(!wideMode) };
    const fullscreenOnClick = {
      click: () => setCodeModalVisibility(true)
    };

    const descriptionText = this.readOnly ? null : codeEditorText;

    return (
      <b-form-group id={`code-editor-group-${selectedNode.id}`} description={descriptionText}>
        <div class="display--flex">
          <label class="d-block flex-grow--1 padding-top--normal" htmlFor={`code-editor-${selectedNode.id}`}>
            {this.readOnly ? 'View' : 'Edit'} Block Code:
          </label>
          <b-button on={fullscreenOnClick} class="show-block-container__expand-button">
            <span class="fa fa-expand" />
          </b-button>
          <b-button on={expandOnClick} class="show-block-container__expand-button">
            <span class="fa fa-angle-double-left" />
          </b-button>
        </div>
        <div class="input-group with-focus show-block-container__code-editor">{this.renderCodeEditor()}</div>
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
            required={true}
            max={inputProps.max}
            min={inputProps.min}
            step={inputProps.step}
            readonly={inputProps.readOnly}
            disabled={inputProps.disabled}
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
    const changeCodeLanguage = this.readOnly ? nopWrite : this.changeCodeLanguage;

    return (
      <b-form-group id={`block-language-group-${selectedNode.id}`} description={languagesText}>
        <label class="d-block" htmlFor={`block-language-${selectedNode.id}`}>
          Block Runtime:
        </label>
        <div class="input-group with-focus">
          <b-form-select
            id={`block-language-${selectedNode.id}`}
            value={this.selectedNode.language}
            readonly={this.readOnly}
            disabled={this.readOnly}
            on={{ input: changeCodeLanguage }}
            options={Object.values(SupportedLanguage)}
          />
        </div>
      </b-form-group>
    );
  }

  deleteLibrary(library: string) {
    // Do nothing
    if (this.readOnly) {
      return;
    }

    this.deleteDependencyImport(library);
  }

  addLibrary(e: Event) {
    e.preventDefault();

    // Do nothing
    if (this.readOnly) {
      return;
    }

    this.addDependencyImport(this.enteredLibrary);

    // Reset input
    this.setEnteredLibrary('');
  }

  public renderLibraryTable() {
    // If there are no currently-added libraries
    if (this.selectedNode.libraries.length === 0) {
      return (
        <div class="text-center">
          <i>You currently have no libraries! Add one below.</i>
          <br />
          <a href={LanguageToBaseRepoURLMap[this.selectedNode.language]} target="_blank">
            Click here to find a library for your Code Block.
          </a>
        </div>
      );
    }

    const libraryTable = this.selectedNode.libraries.map(library => {
      const packageRepoLink = LanguageToLibraryRepoURLMap[this.selectedNode.language] + encodeURIComponent(library);
      return (
        <b-list-group-item class="d-flex">
          <span class="float-left d-inline">
            <a href={packageRepoLink} target="_blank">
              {library}
            </a>
          </span>
          <div class="ml-auto float-right d-inline">
            <button type="button" on={{ click: this.deleteLibrary.bind(this, library) }} class="btn btn-danger">
              <span class="fas fa-trash" />
            </button>
          </div>
        </b-list-group-item>
      );
    });
    return <b-list-group>{libraryTable}</b-list-group>;
  }

  public closeLibraryModal() {
    if (this.selectedNode === null || this.selectedNode.type !== WorkflowStateType.LAMBDA) {
      console.error("You don't have a node currently selected so I can't check the build status!");
      return;
    }
    const libraries = deepJSONCopy(this.selectedNode.libraries);
    const params: libraryBuildArguments = {
      language: this.selectedNode.language as SupportedLanguage,
      libraries: libraries
    };
    startLibraryBuild(params);
    this.setLibrariesModalVisibility(false);
  }

  public renderLibrariesModal() {
    if (!this.selectedNode) {
      return;
    }

    const librariesModalVisibility = this.readOnly
      ? this.librariesModalVisibilityDeployment
      : this.librariesModalVisibility;

    const enteredLibrary = this.readOnly ? '' : this.enteredLibrary;
    const setEnteredLibrary = this.readOnly ? nopWrite : this.setEnteredLibrary;

    const modalOnHandlers = {
      hidden: () => this.closeLibraryModal()
    };

    return (
      <b-modal
        ref={`libraries-modal-${this.selectedNode.id}`}
        on={modalOnHandlers}
        footer-class="p-2"
        title="Select the libraries for your Code Block"
        visible={librariesModalVisibility}
        ok-only={true}
        ok-variant="secondary"
        ok-title="Close"
      >
        {this.renderLibraryTable()}

        <hr />
        <b-form on={{ submit: this.addLibrary }}>
          <b-form-group
            label="Library name:"
            label-for="library-input-field"
            description="The name of the library you want to install as a dependency."
          >
            <b-form-input
              id="library-input-field"
              type="text"
              required={true}
              placeholder="Enter your library name"
              readonly={this.readOnly}
              disabled={this.readOnly}
              value={enteredLibrary}
              on={{ input: setEnteredLibrary }}
            />
          </b-form-group>
          <b-button type="submit" variant="primary">
            Add Library
          </b-button>
        </b-form>
      </b-modal>
    );
  }

  private viewLibraryModal() {
    const setEnteredLibrary = this.readOnly ? nopWrite : this.setEnteredLibrary;

    // Reset library name input
    setEnteredLibrary('');
    this.setLibrariesModalVisibility(true);
  }

  public renderLibrarySelector() {
    // Go has no libraries, it's done via in-code imports
    if (this.selectedNode.language === SupportedLanguage.GO1_12) {
      return <div />;
    }
    return (
      <b-form-group description="The libraries to install for your Block Code.">
        <label class="d-block">Block Imported Libraries:</label>
        <b-button variant="dark" class="col-12" on={{ click: this.viewLibraryModal }}>
          Modify Libraries (<i>{this.selectedNode.libraries.length.toString()} Imported</i>)
        </b-button>
      </b-form-group>
    );
  }

  public renderAwsLink() {
    if (!this.readOnly) {
      return null;
    }

    return (
      <b-form-group description="Click to open this resource in the AWS Console.">
        <label class="d-block">View in AWS Console:</label>
        <b-button
          variant="dark"
          class="col-12 mb-1"
          href={this.getAwsConsoleUri}
          on={{ click: preventDefaultWrapper(this.openAwsConsoleForBlock) }}
        >
          Inspect Block Instance
        </b-button>
        <b-button
          variant="dark"
          class="col-12 mb-1"
          href={this.getLambdaMonitorUri}
          on={{ click: preventDefaultWrapper(this.openAwsMonitorForCodeBlock) }}
        >
          CloudWatch Logs
        </b-button>
        <b-button
          variant="dark"
          class="col-12"
          href={this.getLambdaCloudWatchUri}
          on={{ click: preventDefaultWrapper(this.openAwsCloudwatchForCodeBlock) }}
        >
          Block History Monitor
        </b-button>
      </b-form-group>
    );
  }

  public render(): VNode {
    const setMaxExecutionTime = this.readOnly ? nopWrite : this.setMaxExecutionTime;
    const setExecutionMemory = this.readOnly ? nopWrite : this.setExecutionMemory;

    const maxExecutionTimeProps: FormProps = {
      idPrefix: 'max-execution',
      description: maxExecutionTimeText,
      name: 'Max Execution Time (seconds)',
      placeholder: '30',
      min: 15,
      max: 60 * 15,
      step: 15,

      type: 'number',
      readonly: this.readOnly,
      disabled: this.readOnly,
      value: this.selectedNode.max_execution_time.toString(),
      on: { change: setMaxExecutionTime }
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
      readonly: this.readOnly,
      disabled: this.readOnly,
      value: this.selectedNode.memory.toString(),
      on: { change: setExecutionMemory }
    };

    // Fork the display for read-only/deployment view to make the UX more clear for what pane the user is in.
    if (this.readOnly) {
      return (
        <div>
          <BlockDocumentationButton props={{ docLink: 'https://docs.refinery.io/blocks/#code-block' }} />
          <BlockNameInput props={{ selectedNode: this.selectedNode, readOnly: this.readOnly }} />
          {this.renderAwsLink()}
          {this.renderCodeEditorContainer()}
          {this.renderLanguageSelector()}
          {this.renderForm(this.selectedNode, maxExecutionTimeProps)}
          {this.renderForm(this.selectedNode, maxMemoryProps)}
          {this.renderCodeEditorModal()}
        </div>
      );
    }

    return (
      <div>
        <BlockDocumentationButton props={{ docLink: 'https://docs.refinery.io/blocks/#code-block' }} />
        <BlockNameInput props={{ selectedNode: this.selectedNode, readOnly: this.readOnly }} />
        {this.renderCodeEditorContainer()}
        {this.renderAwsLink()}
        {this.renderLibrarySelector()}
        {/*<b-button variant="dark" class="col-12 mb-3">*/}
        {/*  Edit Environment Variables*/}
        {/*</b-button>*/}
        {this.renderLanguageSelector()}
        {this.renderForm(this.selectedNode, maxExecutionTimeProps)}
        {this.renderForm(this.selectedNode, maxMemoryProps)}
        {this.renderCodeEditorModal()}
        {this.renderLibrariesModal()}
      </div>
    );
  }
}
