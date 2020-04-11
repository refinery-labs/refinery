import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { ProjectConfig, ProjectLogLevel, SupportedLanguage } from '@/types/graph';
import { namespace } from 'vuex-class';
import { languages } from 'monaco-editor';
import Loading from '@/components/Common/Loading.vue';
import { LoadingContainerProps } from '@/types/component-types';

const project = namespace('project');

@Component
export default class ProjectSettings extends Vue {
  @project.State openedProjectConfig!: ProjectConfig | null;

  @project.Action setProjectConfigLoggingLevel!: (projectConfigLoggingLevel: ProjectLogLevel) => void;
  @project.Action setProjectConfigRuntimeLanguage!: (projectConfigRuntimeLanguage: SupportedLanguage) => void;
  @project.Action setProjectConfigRepo!: (projectConfigRepo: string) => void;

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

  private renderProjectRepo() {
    return (
      <b-form-group description="The git repository where blocks can be imported from.">
        <label class="d-block" htmlFor="git-repo-input">
          Project Git Repository
        </label>
        <div class="input-group with-focus">
          <b-form-input id="git-repo-input" value={this.getProjectRepo()} on={{ change: this.setProjectConfigRepo }} />
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
            {this.renderProjectRepo()}
            {this.renderLogLevel()}
            {this.renderRuntimeLanguage()}
          </div>
        </div>
      </Loading>
    );
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
      </div>
    );
  }
}
