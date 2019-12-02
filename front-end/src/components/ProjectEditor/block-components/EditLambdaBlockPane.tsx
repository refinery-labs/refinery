import Component from 'vue-class-component';
import Vue, { VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { LambdaWorkflowState, SupportedLanguage, WorkflowState, WorkflowStateType } from '@/types/graph';
import { FormProps, LanguageToBaseRepoURLMap, LanguageToLibraryRepoURLMap } from '@/types/project-editor-types';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import Loading from '@/components/Common/Loading.vue';
import { namespace } from 'vuex-class';
import {
  codeEditorText,
  languagesText,
  maxExecutionMemoryText,
  maxExecutionTimeText
} from '@/constants/project-editor-constants';
import RunEditorCodeBlockContainer from '@/components/ProjectEditor/RunEditorCodeBlockContainer';
import RunDeployedCodeBlockContainer from '@/components/DeploymentViewer/RunDeployedCodeBlockContainer';
import { nopWrite } from '@/utils/block-utils';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditBlockPaneProps, EditorProps, LoadingContainerProps } from '@/types/component-types';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { BlockDocumentationButton } from '@/components/ProjectEditor/block-components/EditBlockDocumentationButton';
import {
  EditEnvironmentVariablesWrapper,
  EditEnvironmentVariablesWrapperProps
} from '@/components/ProjectEditor/block-components/EditEnvironmentVariablesWrapper';
import { SavedBlockStatusCheckResult, SavedBlockSaveType } from '@/types/api-types';
import Split from '@/components/Common/Split.vue';
import SplitArea from '@/components/Common/SplitArea.vue';
import { RunLambdaDisplayMode } from '@/components/RunLambda';
import {
  EditBlockLayersWrapper,
  EditBlockLayersWrapperProps
} from '@/components/ProjectEditor/block-components/EditBlockLayersWrapper';
import { languageToFileExtension } from '@/utils/project-debug-utils';
import {
  BlockLocalCodeSyncStoreModule,
  CodeBlockSharedFilesPaneModule,
  CreateSavedBlockViewStoreModule
} from '@/store';
import { syncFileIdPrefix } from '@/store/modules/panes/block-local-code-sync';

const editBlock = namespace('project/editBlockPane');
const viewBlock = namespace('viewBlock');

@Component
export class EditLambdaBlock extends Vue implements EditBlockPaneProps {
  @Prop({ required: true }) selectedNode!: LambdaWorkflowState;
  @Prop({ required: true }) selectedNodeMetadata!: SavedBlockStatusCheckResult | null;
  @Prop({ required: true }) readOnly!: boolean;

  // State pulled from Deployment view.
  @viewBlock.State('showCodeModal') showCodeModalDeployment!: boolean;
  @viewBlock.State('librariesModalVisibility') librariesModalVisibilityDeployment!: boolean;

  @viewBlock.Getter getAwsConsoleUri!: string | null;
  @viewBlock.Getter getLambdaMonitorUri!: string | null;
  @viewBlock.Getter getLambdaCloudWatchUri!: string | null;

  @viewBlock.Mutation('setCodeModalVisibility') setCodeModalVisibilityDeployment!: (visible: boolean) => void;
  @viewBlock.Mutation('setLibrariesModalVisibility') setLibrariesModalVisibilityDeployment!: (
    visibility: boolean
  ) => void;
  @viewBlock.Action openAwsConsoleForBlock!: () => void;
  @viewBlock.Action openAwsMonitorForCodeBlock!: () => void;
  @viewBlock.Action openAwsCloudwatchForCodeBlock!: () => void;
  @viewBlock.Action('runCodeBlock') runDeployedCodeBlock!: () => void;
  @viewBlock.Action('downloadBlockAsZip') downloadDeployedBlockAsZip!: () => void;

  // State pulled from Project view
  @editBlock.State showCodeModal!: boolean;
  @editBlock.State librariesModalVisibility!: boolean;
  @editBlock.State enteredLibrary!: string;
  @editBlock.State isLoadingMetadata!: boolean;
  @editBlock.State changeLanguageWarningVisible!: boolean;
  @editBlock.State nextLanguageToChangeTo!: SupportedLanguage | null;
  @editBlock.State replaceCodeWithTemplateChecked!: boolean;
  @editBlock.State fileToSyncBlockWith!: string | null;
  @editBlock.State fileSyncModalVisible!: boolean;

  @editBlock.Getter isEditedBlockValid!: boolean;

  @editBlock.Mutation setCodeModalVisibility!: (visible: boolean) => void;

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
  @editBlock.Mutation setConcurrencyLimit!: (limit: number | false) => void;
  @editBlock.Mutation resetChangeLanguageModal!: () => void;
  @editBlock.Mutation setReplaceCodeWithTemplateChecked!: (checked: boolean) => void;

  @editBlock.Action saveBlock!: () => Promise<void>;
  @editBlock.Action updateSavedBlockVersion!: () => Promise<void>;
  @editBlock.Action kickOffLibraryBuild!: () => void;
  @editBlock.Action showChangeLanguageWarning!: (language: SupportedLanguage) => void;
  @editBlock.Action changeBlockLanguage!: () => void;
  @editBlock.Action('runCodeBlock') runEditorCodeBlock!: () => void;
  @editBlock.Action('downloadBlockAsZip') downloadEditorBlockAsZip!: () => void;
  @editBlock.Action('downloadBlockScript') downloadBlockScript!: () => void;
  @editBlock.Action syncBlockWithFile!: () => Promise<void>;
  @editBlock.Action setFileSyncModalVisibility!: (visible: boolean) => Promise<void>;

  deleteLibrary(library: string) {
    // Do nothing
    if (this.readOnly) {
      return;
    }

    this.deleteDependencyImport(library);
  }

  public async beginPublishBlockClicked(e: Event) {
    e.preventDefault();
    await this.saveBlock();

    CreateSavedBlockViewStoreModule.openModal(SavedBlockSaveType.CREATE);
  }

  public async beginForkBlockClicked(e: Event) {
    e.preventDefault();
    await this.saveBlock();

    CreateSavedBlockViewStoreModule.openModal(SavedBlockSaveType.FORK);
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

  public changeCodeLanguage(language: SupportedLanguage) {
    this.showChangeLanguageWarning(language);
  }

  public closeLibraryModal() {
    this.kickOffLibraryBuild();
  }

  private viewLibraryModal() {
    const setEnteredLibrary = this.readOnly ? nopWrite : this.setEnteredLibrary;

    // Reset library name input
    setEnteredLibrary('');
    this.setLibrariesModalVisibility(true);
  }

  public renderChangeLanguageWarning() {
    if (!this.changeLanguageWarningVisible) {
      return null;
    }

    const modalOnHandlers = {
      hidden: () => this.resetChangeLanguageModal()
    };

    return (
      <b-modal
        on={modalOnHandlers}
        hide-footer={true}
        title={`Change Block Language to ${this.nextLanguageToChangeTo}?`}
        visible={this.changeLanguageWarningVisible}
      >
        <b-form on={{ submit: preventDefaultWrapper(() => this.changeBlockLanguage()) }}>
          <h4>Warning! You may break something!</h4>
          <p>This will remove all libraries, if you have any specified.</p>
          <p>Changing the language will likely make your code no longer function.</p>

          <b-form-group id="change-language-input-group">
            <b-form-checkbox
              id="change-language-input"
              name="change-language-input"
              on={{ change: () => this.setReplaceCodeWithTemplateChecked(!this.replaceCodeWithTemplateChecked) }}
              readonly={this.readOnly}
              disabled={this.readOnly}
              checked={this.replaceCodeWithTemplateChecked}
            >
              Replace code with default template?
            </b-form-checkbox>
          </b-form-group>

          <div class="display--flex">
            <b-button class="mr-1 ml-1 flex-grow--1 width--100percent" variant="danger" type="submit">
              Confirm Change
            </b-button>
          </div>
        </b-form>
      </b-modal>
    );
  }

  public renderCodeEditorModal() {
    const nameString = `${this.readOnly ? 'Viewing' : 'Editing'} Code for '${this.selectedNode.name}'`;

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
        no-close-on-esc={true}
        size="xl no-max-width no-modal-body-padding dark-modal"
        title={nameString}
        visible={showCodeModal}
      >
        <div class="display--flex code-modal-editor-container overflow--hidden-x">
          <Split
            props={{
              direction: 'horizontal' as Object,
              extraClasses: 'height--100percent flex-grow--1 display--flex' as Object
            }}
          >
            <SplitArea props={{ size: 67 as Object, positionRelative: true as Object }}>
              {this.renderCodeEditor('ace-hack', true)}
            </SplitArea>
            <SplitArea props={{ size: 33 as Object }}>
              <RunLambdaContainer props={{ displayMode: RunLambdaDisplayMode.fullscreen }} />
            </SplitArea>
          </Split>
        </div>
      </b-modal>
    );
  }

  public renderCodeEditor(extraClasses?: string, disableFullscreen?: boolean) {
    const setCodeInput = this.readOnly ? nopWrite : this.setCodeInput;

    const setCodeModalVisibility = this.readOnly ? this.setCodeModalVisibilityDeployment : this.setCodeModalVisibility;

    const isCurrentlySynced = BlockLocalCodeSyncStoreModule.isBlockBeingSynced(this.selectedNode.id);

    const editorProps: EditorProps = {
      name: `block-code-${this.selectedNode.id}`,
      lang: this.selectedNode.language,
      readOnly: this.readOnly || isCurrentlySynced,
      content: this.selectedNode.code,
      onChange: setCodeInput,
      fullscreenToggled: () => setCodeModalVisibility(true),
      disableFullscreen: disableFullscreen
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  public renderCodeEditorContainer() {
    const selectedNode = this.selectedNode;

    const runCodeBlock = this.readOnly ? this.runDeployedCodeBlock : this.runEditorCodeBlock;
    const setCodeModalVisibility = this.readOnly ? this.setCodeModalVisibilityDeployment : this.setCodeModalVisibility;

    const runCodeOnClick = {
      click: () => runCodeBlock()
    };

    const fullscreenOnClick = {
      click: () => setCodeModalVisibility(true)
    };

    const descriptionText = this.readOnly ? null : codeEditorText;

    return (
      <b-form-group id={`code-editor-group-${selectedNode.id}`} description={descriptionText}>
        <div class="display--flex flex-wrap">
          <label class="d-block flex-grow--1 padding-top--normal" htmlFor={`code-editor-${selectedNode.id}`}>
            {this.readOnly ? 'View' : 'Edit'} Block Code:
          </label>
          <div class="flex-grow--1 display--flex">
            <b-button
              on={runCodeOnClick}
              class="show-block-container__expand-button mr-2 flex-grow--1"
              variant="outline-success"
            >
              <span class="icon-control-play" />
              {'  '}Run Code
            </b-button>
            <b-button on={fullscreenOnClick} class="show-block-container__expand-button mr-2 flex-grow--1">
              <span class="fa fa-expand" />
              {'  '}Open Full {this.readOnly ? 'Viewer' : 'Editor'}
            </b-button>
            <BlockDocumentationButton
              props={{ docLink: 'https://docs.refinery.io/blocks/#code-block', offsetButton: false }}
            />
          </div>
        </div>
        <div class="input-group with-focus show-block-container__code-editor">{this.renderCodeEditor()}</div>
      </b-form-group>
    );
  }

  public renderForm(selectedNode: WorkflowState, inputProps: FormProps) {
    const { idPrefix, name, description, type, on } = inputProps;

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
            on={inputProps.on}
            {...inputProps}
          />
        </div>
      </b-form-group>
    );
  }

  public renderConcurrencyLimit(selectedNode: LambdaWorkflowState) {
    const hasLimitSet =
      selectedNode.reserved_concurrency_count !== undefined && selectedNode.reserved_concurrency_count !== false;
    const description = <span>If toggled, this allows you to limit the maximum concurrency for a given block.</span>;

    const extendedDescription = (
      <span>
        {description}
        This behaviour also has other implications, which we recommend you familiarize yourself with before using this
        feature by{' '}
        <a
          href="https://docs.aws.amazon.com/lambda/latest/dg/concurrent-executions.html#per-function-concurrency"
          target="_blank"
        >
          reviewing the docs
        </a>
        .
      </span>
    );

    const concurrentLimitInput = (
      <div>
        <label class="d-block" htmlFor={`concurrency-limit-amount-${selectedNode.id}`}>
          Concurrency Limit:
        </label>
        <div class="input-group with-focus">
          <b-form-input
            id={`concurrency-limit-amount-${selectedNode.id}`}
            type="number"
            required={true}
            max={100}
            min={1}
            readonly={this.readOnly}
            disabled={!hasLimitSet}
            on={{
              update: this.setConcurrencyLimit,
              blur: () => this.setConcurrencyLimit(selectedNode.reserved_concurrency_count)
            }}
            value={selectedNode.reserved_concurrency_count}
          />
        </div>
        <b-form-invalid-feedback state={selectedNode.reserved_concurrency_count < 20}>
          Warning: Setting this high of a concurrency will limit will reduce your maximum concurrency for all other
          blocks.
        </b-form-invalid-feedback>
      </div>
    );

    return (
      <b-form-group id={`concurrency-limit-group-${selectedNode.id}`}>
        <b-form-checkbox
          id={`concurrency-limit-toggle-${selectedNode.id}`}
          name="concurrency-limit-toggle"
          on={{ change: () => this.setConcurrencyLimit(hasLimitSet ? false : 1) }}
          readonly={this.readOnly}
          disabled={this.readOnly}
          checked={hasLimitSet}
        >
          Limit Block Concurrency
        </b-form-checkbox>
        {hasLimitSet && concurrentLimitInput}
        <span class="form-text text-muted">{hasLimitSet ? extendedDescription : description}</span>
      </b-form-group>
    );
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
        no-close-on-esc={true}
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

  public renderCreateSavedBlockButton() {
    if (this.readOnly) {
      return null;
    }

    if (this.isLoadingMetadata) {
      const loadingProps: LoadingContainerProps = {
        label: 'Loading saved block status...',
        show: true
      };

      return (
        <Loading props={loadingProps}>
          <div style={{ height: '100px' }} />
        </Loading>
      );
    }

    const hasNewerVersionAvailable =
      this.selectedNodeMetadata &&
      this.selectedNode.saved_block_metadata &&
      this.selectedNodeMetadata.version > this.selectedNode.saved_block_metadata.version;

    if (hasNewerVersionAvailable) {
      return (
        <b-form-group description="Clicking this will update this block to the latest version. Warning: This will discard changes any you have made to the block!">
          <label class="d-block">New Saved Block Version Available!</label>
          <b-button variant="dark" class="col-12" on={{ click: this.updateSavedBlockVersion }}>
            Update Block
          </b-button>
        </b-form-group>
      );
    }

    if (this.selectedNodeMetadata && this.selectedNodeMetadata.is_block_owner) {
      return (
        <b-form-group description="Allows you to publish a new version or fork this block.">
          <label class="d-block">Manage Saved Block:</label>
          <b-button
            variant="dark"
            class="col-12"
            disabled={!this.isEditedBlockValid}
            on={{ click: this.beginPublishBlockClicked }}
          >
            Publish New Block Version
          </b-button>
          <b-button
            variant="dark"
            class="col stacked-edit-block-button"
            disabled={!this.isEditedBlockValid}
            on={{ click: this.beginForkBlockClicked }}
          >
            Fork Block Version
          </b-button>
        </b-form-group>
      );
    }

    // Just don't show this... For now. Eventually when we implement update this should be an "Update Block" button.
    if (this.selectedNodeMetadata) {
      return null;
    }

    return (
      <b-form-group description="Save this block to use in other projects. You may also publish this block on the Community Block Repository for use by others.">
        <label class="d-block">Create Saved Block:</label>
        <b-button
          variant="dark"
          class="col-12"
          disabled={!this.isEditedBlockValid}
          on={{ click: this.beginPublishBlockClicked }}
        >
          Create Saved Block
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
          Open Lambda in AWS
        </b-button>
        <b-button
          variant="dark"
          class="col-12 mb-1"
          href={this.getLambdaMonitorUri}
          on={{ click: preventDefaultWrapper(this.openAwsMonitorForCodeBlock) }}
        >
          CloudWatch Graphs
        </b-button>
        <b-button
          variant="dark"
          class="col-12"
          href={this.getLambdaCloudWatchUri}
          on={{ click: preventDefaultWrapper(this.openAwsCloudwatchForCodeBlock) }}
        >
          CloudWatch Logs
        </b-button>
      </b-form-group>
    );
  }

  public renderBlockVariables() {
    const editEnvironmentVariablesWrapperProps: EditEnvironmentVariablesWrapperProps & EditBlockPaneProps = {
      selectedNode: this.selectedNode,
      selectedNodeMetadata: null,
      readOnly: this.readOnly
    };

    return (
      <b-form-group description="Click to view the variables passed to the block at runtime.">
        <label class="d-block">Block Environment Variables:</label>
        <EditEnvironmentVariablesWrapper props={editEnvironmentVariablesWrapperProps} />
      </b-form-group>
    );
  }

  public renderBlockLayers() {
    const blockLayersEditorWrapperProps: EditBlockLayersWrapperProps & EditBlockPaneProps = {
      selectedNode: this.selectedNode,
      selectedNodeMetadata: null,
      readOnly: this.readOnly
    };

    return (
      <b-form-group description="Click to add AWS Lambda Layers to the runtime environment.">
        <label class="d-block">Block Layers (Lambda Layers):</label>
        <EditBlockLayersWrapper props={blockLayersEditorWrapperProps} />
      </b-form-group>
    );
  }

  public renderDownloadBlock() {
    const downloadBlockAsZip = this.readOnly ? this.downloadDeployedBlockAsZip : this.downloadEditorBlockAsZip;

    return (
      <b-form-group description="Creates and downloads a zip of the current code block, including code to help develop the code block locally.">
        <label class="d-block">Run Block Code Locally:</label>
        <b-button variant="dark" class="col-12" on={{ click: downloadBlockAsZip }}>
          Download Block as Zip
        </b-button>
        <b-button variant="dark" class="col stacked-edit-block-button" on={{ click: this.downloadBlockScript }}>
          Download Block Script
        </b-button>
      </b-form-group>
    );
  }

  public renderLocalFileLinkButton() {
    const isCurrentlySynced = BlockLocalCodeSyncStoreModule.isBlockBeingSynced(this.selectedNode.id);

    function getOnClickHandler() {
      if (isCurrentlySynced) {
        return BlockLocalCodeSyncStoreModule.stopSyncJobForSelectedBlock;
      }

      return BlockLocalCodeSyncStoreModule.OpenSyncFileModal;
    }

    function getDescriptionText() {
      if (isCurrentlySynced) {
        return 'This block is currently being synced with a file. Click the button to cancel this job and resume editing this block\'s code in the editor.';
      }

      return 'Click to select a file that will replace the contents of this block. This may also continually refresh the block\'s content.';
    }

    function getButtonText() {
      if (isCurrentlySynced) {
        return 'Stop File Sync';
      }

      return 'Open File';
    }

    // Used to disable this feature because we are effectively abusing a bug in Chrome.
    const hasChromeBrowser = window.navigator.userAgent && /Chrome/.test(window.navigator.userAgent);

    return (
      <div>
        <b-form-group description={getDescriptionText()}>
          <label class="d-block">Sync Block With Local File:</label>
          <b-button variant="dark" class="col-12" on={{ click: getOnClickHandler() }} disabled={!hasChromeBrowser}>
            {getButtonText()}
          </b-button>
        </b-form-group>
      </div>
    );
  }

  public renderSelectLocalFileToSyncModal() {
    if (!BlockLocalCodeSyncStoreModule.localFileSyncModalVisible) {
      return null;
    }

    if (BlockLocalCodeSyncStoreModule.localFileSyncModalUniqueId === null) {
      throw new Error('Local file sync modal ID is null, this is bad and the app is breaking now');
    }

    const selectedBlock = BlockLocalCodeSyncStoreModule.selectedBlockForModal;

    if (!selectedBlock) {
      throw new Error('Cannot render select local file modal without block in store');
    }

    const uniqueId = BlockLocalCodeSyncStoreModule.localFileSyncModalUniqueId;

    const modalOnHandlers = {
      hidden: () => BlockLocalCodeSyncStoreModule.resetModal()
    };

    const expectedFileExtension = `.${languageToFileExtension[this.selectedNode.language]}`;

    return (
      <b-modal
        on={modalOnHandlers}
        hide-footer={true}
        title={`Sync Local Code with ${selectedBlock.name}`}
        visible={BlockLocalCodeSyncStoreModule.localFileSyncModalVisible}
      >
        <b-form on={{ submit: preventDefaultWrapper(() => BlockLocalCodeSyncStoreModule.addBlockWatchJob()) }}>
          <h4>Please choose a file from your local file system.</h4>
          <p>
            When you update the file on your system, the block code will automatically update to match the file
            contents.
          </p>
          <p>This sync will stop when you refresh your browser or close this project.</p>

          <b-form-group
            id="sync-local-file-input-group"
            label="Select local file:"
            label-for="sync-local-file-input"
            description="The file that you choose will be automatically synchronized to the block."
          >
            <b-form-file
              id={`${syncFileIdPrefix}${uniqueId}`}
              class="mb-2 mr-sm-2 mb-sm-0"
              accept={expectedFileExtension}
              required={true}
              placeholder={`eg, my-amazing-code${expectedFileExtension}`}
            />
          </b-form-group>

          <b-form-group id="local-file-auto-run-input-group">
            <b-form-checkbox
              id="local-file-auto-run-input"
              name="local-file-auto-run-input"
              on={{
                change: () =>
                  BlockLocalCodeSyncStoreModule.setExecuteBlockOnFileChangeToggled(
                    !BlockLocalCodeSyncStoreModule.executeBlockOnFileChangeToggled
                  )
              }}
              checked={BlockLocalCodeSyncStoreModule.executeBlockOnFileChangeToggled}
            >
              Automatically execute when file is changed?
            </b-form-checkbox>
          </b-form-group>

          <div class="display--flex">
            <b-button class="mr-1 ml-1 flex-grow--1 width--100percent" variant="primary" type="submit">
              Confirm Add
            </b-button>
          </div>
        </b-form>
      </b-modal>
    );
  }

  public renderSharedFiles() {
    return (
      <b-form-group description="Shared Files linked to this Code Block.">
        <label class="d-block">Shared Files:</label>
        <b-button
          variant="dark"
          class="col-12"
          on={{ click: () => CodeBlockSharedFilesPaneModule.openCodeBlockSharedFiles(this.selectedNode) }}
        >
          View Block Shared Files
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
      value: this.selectedNode.max_execution_time,
      on: { change: setMaxExecutionTime, blur: () => setMaxExecutionTime(this.selectedNode.max_execution_time) }
    };

    const maxMemoryProps: FormProps = {
      idPrefix: 'max-memory',
      description: maxExecutionMemoryText,
      name: 'Instance Max Memory Size (MBs)',
      placeholder: '768',
      type: 'number',
      number: true,
      max: 3008,
      min: 128,
      step: 64,
      readonly: this.readOnly,
      disabled: this.readOnly,
      value: this.selectedNode.memory,
      on: { change: setExecutionMemory, blur: () => setExecutionMemory(this.selectedNode.memory) }
    };

    const editBlockProps: EditBlockPaneProps = {
      selectedNode: this.selectedNode,
      selectedNodeMetadata: this.selectedNodeMetadata,
      readOnly: this.readOnly
    };

    const blockNameRow = (
      <b-col cols={12}>
        <div class="shift-code-block-editor">
          <BlockNameInput props={editBlockProps} />
        </div>
      </b-col>
    );

    const codeEditorRow = (
      <b-col cols={12}>
        <div class="mt-2">{this.renderCodeEditorContainer()}</div>
      </b-col>
    );

    // Fork the display for read-only/deployment view to make the UX more clear for what pane the user is in.
    if (this.readOnly) {
      return (
        <div class="show-block-container__block row">
          {codeEditorRow}
          {blockNameRow}

          <b-col xl={6}>{this.renderAwsLink()}</b-col>

          <b-col xl={6}>{this.renderBlockVariables()}</b-col>
          <b-col xl={6}>{this.renderBlockLayers()}</b-col>
          <b-col xl={6}>{this.renderLanguageSelector()}</b-col>
          <b-col xl={6}>{this.renderDownloadBlock()}</b-col>
          <b-col xl={6}>{this.renderForm(this.selectedNode, maxExecutionTimeProps)}</b-col>
          <b-col xl={6}>{this.renderForm(this.selectedNode, maxMemoryProps)}</b-col>
          <b-col xl={6}>{this.renderConcurrencyLimit(this.selectedNode)}</b-col>
          {this.renderCodeEditorModal()}
        </div>
      );
    }

    return (
      <div class="show-block-container__block row">
        {codeEditorRow}
        {blockNameRow}

        <b-col xl={6}>{this.renderCreateSavedBlockButton()}</b-col>
        <b-col xl={6}>{this.renderBlockVariables()}</b-col>
        <b-col xl={6}>{this.renderBlockLayers()}</b-col>
        <b-col xl={6}>{this.renderLibrarySelector()}</b-col>
        <b-col xl={6}>{this.renderLocalFileLinkButton()}</b-col>
        <b-col xl={6}>{this.renderDownloadBlock()}</b-col>
        <b-col xl={6}>{this.renderLanguageSelector()}</b-col>
        <b-col xl={6}>{this.renderSharedFiles()}</b-col>
        <b-col xl={6}>{this.renderForm(this.selectedNode, maxExecutionTimeProps)}</b-col>
        <b-col xl={6}>{this.renderForm(this.selectedNode, maxMemoryProps)}</b-col>
        <b-col xl={6}>{this.renderConcurrencyLimit(this.selectedNode)}</b-col>
        {this.renderCodeEditorModal()}
        {this.renderLibrariesModal()}
        {this.renderChangeLanguageWarning()}
        {this.renderSelectLocalFileToSyncModal()}
      </div>
    );
  }
}
