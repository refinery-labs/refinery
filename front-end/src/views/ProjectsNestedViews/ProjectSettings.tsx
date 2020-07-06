import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import {
  LambdaWorkflowState,
  ProjectConfig,
  ProjectLogLevel,
  RefineryProject,
  SupportedLanguage,
  WorkflowStateType
} from '@/types/graph';
import { namespace } from 'vuex-class';
import Loading from '@/components/Common/Loading.vue';
import { LoadingContainerProps } from '@/types/component-types';
import RepoSelectionModal from '@/components/ProjectSettings/RepoSelectionModal';

const project = namespace('project');
const repoSelectionModal = namespace('repoSelectionModal');

@Component
export default class ProjectSettings extends Vue {
  @project.State openedProject!: RefineryProject | null;
  @project.State openedProjectConfig!: ProjectConfig | null;

  @repoSelectionModal.Mutation setRepoSelectionModalVisible!: (showing: boolean) => void;

  @repoSelectionModal.Action cacheReposForUser!: () => void;
  @project.Action setProjectConfigLoggingLevel!: (projectConfigLoggingLevel: ProjectLogLevel) => void;
  @project.Action setProjectConfigRuntimeLanguage!: (projectConfigRuntimeLanguage: SupportedLanguage) => void;
  @project.Action setProjectGlobalExceptionHandlerToNode!: (nodeId: string | null) => void;

  private isSettingGlobalExceptionHandler: boolean = false;

  private getLogLevelValue() {
    // TODO: Move this business logic to an action in the store.
    if (!this.openedProjectConfig || !this.openedProjectConfig.logging || !this.openedProjectConfig.logging.level) {
      return ProjectLogLevel.LOG_ALL;
    }
    return this.openedProjectConfig.logging.level;
  }

  private getDefaultRuntimeLanguage() {
    // TODO: Move this business logic to an action in the store.
    if (!this.openedProjectConfig || !this.openedProjectConfig.default_language) {
      return SupportedLanguage.NODEJS_8;
    }
    return this.openedProjectConfig.default_language;
  }

  private getProjectRepo() {
    // TODO: Move this business logic to an action in the store.
    if (!this.openedProjectConfig || !this.openedProjectConfig.project_repo) {
      return '';
    }
    return this.openedProjectConfig.project_repo;
  }

  private getGlobalExceptionHandler(): string | undefined {
    if (!this.openedProject || !this.openedProject.global_handlers.exception_handler) {
      return undefined;
    }
    return this.openedProject.global_handlers.exception_handler.id;
  }

  private getLambdaWorkflowStates(): LambdaWorkflowState[] {
    if (!this.openedProject) {
      return [];
    }
    return this.openedProject.workflow_states
      .filter(w => w.type === WorkflowStateType.LAMBDA)
      .map(w => w as LambdaWorkflowState);
  }

  private async setIsSettingGlobalExceptionHandler(checked: boolean) {
    this.isSettingGlobalExceptionHandler = checked;
    if (!checked) {
      await this.setProjectGlobalExceptionHandlerToNode(null);
    }
  }

  private showSelectRepoModal() {
    this.setRepoSelectionModalVisible(true);
  }

  private renderLogLevel() {
    return (
      <b-form-group description="The logging level to use when Code Blocks run in production. Note that changing this level requires a re-deploy to take effect!">
        <label class="d-block" htmlFor="logging-level-input-select">
          Logging Level
        </label>
        <div class="input-group with-focus">
          <b-form-select
            id="logging-level-input-select"
            value={this.getLogLevelValue()}
            on={{ change: this.setProjectConfigLoggingLevel }}
          >
            <option value={ProjectLogLevel.LOG_ALL}>Log all executions</option>
            <option value={ProjectLogLevel.LOG_ERRORS}>Log only errors</option>
            <option value={ProjectLogLevel.LOG_NONE}>No logging</option>
          </b-form-select>
        </div>
      </b-form-group>
    );
  }

  private renderRuntimeLanguage() {
    const languageOptions = Object.values(SupportedLanguage).map(v => ({
      value: v,
      text: v
    }));

    return (
      <b-form-group description="The default runtime language to use when creating a new block.">
        <label class="d-block" htmlFor="logging-level-input-select">
          Default Runtime Language
        </label>
        <div class="input-group with-focus">
          <b-form-select
            id="logging-level-input-select"
            value={this.getDefaultRuntimeLanguage()}
            on={{ change: this.setProjectConfigRuntimeLanguage }}
            options={languageOptions}
          />
        </div>
      </b-form-group>
    );
  }

  public renderGlobalExceptionHandler() {
    const globalExceptionHandler = this.getGlobalExceptionHandler();

    const exceptionHandlerToggleChecked = globalExceptionHandler !== undefined || this.isSettingGlobalExceptionHandler;
    const disabledExceptionHandlerSelect =
      globalExceptionHandler === undefined && !this.isSettingGlobalExceptionHandler;

    const handlerOptions = this.getLambdaWorkflowStates().map(w => ({
      value: w.id,
      text: w.name
    }));

    return (
      <b-form-group>
        <b-form-checkbox
          id="global-exception-handler-toggle"
          on={{ change: this.setIsSettingGlobalExceptionHandler }}
          disabled={false}
          checked={exceptionHandlerToggleChecked}
        >
          Use a Default Exception Handler Block
        </b-form-checkbox>
        <small>
          Enabling this will add an exception transition to all blocks <em>without an exception transition</em> by
          default. All unhandled exceptions will be handled by the block chosen below.
        </small>
        <b-form-select
          id="logging-level-input-select"
          value={globalExceptionHandler}
          on={{ change: this.setProjectGlobalExceptionHandlerToNode }}
          disabled={disabledExceptionHandlerSelect}
          options={handlerOptions}
        />
      </b-form-group>
    );
  }

  private renderProjectRepo() {
    return (
      <b-form-group description="The git repository where this project will be synced with.">
        <label class="d-block" htmlFor="">
          Project Repository
        </label>
        <div class="input-group with-focus">
          <b-button class="margin-right--small" on={{ click: this.showSelectRepoModal }}>
            Select Project Repo
          </b-button>
          <b-form-input id="project-repo-input" value={this.getProjectRepo()} disabled />
        </div>
      </b-form-group>
    );
  }

  private renderSettingsCard(name: string) {
    const missingProjectConfig = this.openedProjectConfig === null;
    const loadingProps: LoadingContainerProps = {
      show: missingProjectConfig,
      label: 'Loading config values...'
    };

    return (
      <Loading props={loadingProps}>
        <div class="card card-default">
          <div class="card-header">{name}</div>
          <div class="card-body text-align--left">
            {this.renderLogLevel()}
            {this.renderRuntimeLanguage()}
            {this.renderProjectRepo()}
            {this.renderGlobalExceptionHandler()}
          </div>
        </div>
      </Loading>
    );
  }

  public async mounted() {
    await this.cacheReposForUser();
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="content-wrapper">
        <div class="content-heading display-flex">
          <div class="layout--constrain flex-grow--1">
            <div>
              Project Settings
              <small>The settings for this project.</small>
            </div>
          </div>
        </div>
        <div class="layout--constrain">
          <div class="row justify-content-lg-center">
            <div class="col-lg-8 align-self-center">{this.renderSettingsCard('Project Settings')}</div>
          </div>
        </div>
        <RepoSelectionModal />
      </div>
    );
  }
}
