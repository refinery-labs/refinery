import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { ProjectConfig, ProjectLogLevel, SupportedLanguage } from '@/types/graph';
import { namespace } from 'vuex-class';
import Loading from '@/components/Common/Loading.vue';
import { LoadingContainerProps } from '@/types/component-types';
import { GithubRepo } from '@/types/api-types';
import { formatDistanceToNow, fromUnixTime } from 'date-fns';
import { getFriendlyDurationSinceString } from '@/utils/time-utils';

const project = namespace('project');
const projectSettings = namespace('projectSettings');

@Component
export default class ProjectSettings extends Vue {
  private repoSearch: string = '';
  private showingSelectRepoModal: boolean = false;

  @project.State openedProjectConfig!: ProjectConfig | null;
  @projectSettings.State reposForUser?: GithubRepo[] | null;
  @projectSettings.State selectedRepo!: GithubRepo | null;

  @projectSettings.Mutation setSelectedRepo!: (repo: GithubRepo) => void;

  @project.Action setProjectConfigLoggingLevel!: (projectConfigLoggingLevel: ProjectLogLevel) => void;
  @project.Action setProjectConfigRuntimeLanguage!: (projectConfigRuntimeLanguage: SupportedLanguage) => void;
  @project.Action setProjectConfigRepo!: (projectConfigRepo: string) => void;
  @projectSettings.Action listReposForUser!: () => GithubRepo[] | null;
  @projectSettings.Action reorganizeUserRepos!: () => void;

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

  private getCurrentlyConfiguredRepoURL(): string | null {
    if (!this.openedProjectConfig || !this.openedProjectConfig.project_repo) {
      return null;
    }
    return this.openedProjectConfig.project_repo;
  }

  private setShowingSelectRepoModal(showing: boolean) {
    this.showingSelectRepoModal = showing;
    if (!showing) {
      this.reorganizeUserRepos();
    }
  }

  private setRepoSearch(search: string) {
    this.repoSearch = search;
  }

  private async setProjectRepoAndClose() {
    if (this.selectedRepo) {
      await this.setProjectConfigRepo(this.selectedRepo.clone_url);
    }
    this.setShowingSelectRepoModal(false);
  }

  private renderUserRepoItem(repo: GithubRepo) {
    const privateRepoBadge = repo.private ? (
      <b-badge pill={false} class="margin-right--small">
        Private
      </b-badge>
    ) : (
      <div />
    );

    const currentRepoURL = this.getCurrentlyConfiguredRepoURL();
    const isCurrentlyConfiguredRepo = currentRepoURL && currentRepoURL === repo.clone_url;
    const currentConfiguredRepoBadge = isCurrentlyConfiguredRepo ? (
      <b-badge pill={false} variant="primary" class="margin-right--small">
        Current
      </b-badge>
    ) : (
      <div />
    );

    const showingDetails = this.selectedRepo && this.selectedRepo.full_name === repo.full_name;
    const lastUpdatedTime = getFriendlyDurationSinceString(Date.parse(repo.updated_at));

    return (
      <b-card
        no-body
        class="mb-1"
        bg-variant={showingDetails ? 'light' : 'default'}
        className="set-project-repo__description display--flex"
        on={{ click: async () => await this.setSelectedRepo(repo) }}
      >
        <b-card-header header-tag="header" class="p-1" role="tab">
          <div class="d-flex w-100 justify-content-between">
            <h5 class="mb-1">{repo.full_name}</h5>
            <small>
              {currentConfiguredRepoBadge}
              {privateRepoBadge}
              {lastUpdatedTime}
            </small>
          </div>
        </b-card-header>
        <b-collapse id={repo.full_name} visible={showingDetails} accordion="repo-list-accordion" role="tabpanel">
          <b-card-body>
            {repo.description && <p>{repo.description}</p>}
            <small>Stars {repo.stargazers_count}</small>
            <div class="margin-top--normal display--flex justify-content-end align-right">
              <b-button variant="primary" on={{ click: this.setProjectRepoAndClose }}>
                Set repo for project
              </b-button>
            </div>
          </b-card-body>
        </b-collapse>
      </b-card>
    );
  }

  private renderUserRepos() {
    if (this.reposForUser === undefined) {
      return <p>Loading user's repos...</p>;
    }

    if (this.reposForUser === null) {
      return <p>There was an error when getting user's repos.</p>;
    }

    const searchRepoNames = (repo: GithubRepo) => {
      return repo.full_name.toLowerCase().includes(this.repoSearch.toLowerCase());
    };

    return (
      <div role="tablist" class="set-project-repo">
        {this.reposForUser.filter(searchRepoNames).map(this.renderUserRepoItem)}
      </div>
    );
  }

  private renderSelectRepoModal() {
    const modalOnHandlers = {
      hidden: () => this.setShowingSelectRepoModal(false)
    };

    return (
      <b-modal
        on={modalOnHandlers}
        ok-variant="danger"
        footer-class="p-2"
        ref="console-modal"
        hide-footer
        title="Select Project Repo"
        visible={this.showingSelectRepoModal}
      >
        <b-form-input
          class="margin-bottom--normal"
          placeholder="Search for repo..."
          value={this.repoSearch}
          on={{ input: this.setRepoSearch }}
        />
        {this.renderUserRepos()}
      </b-modal>
    );
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
      <b-form-group description="The git repository where this project will be synced with.">
        <div class="input-group with-focus">
          <b-button
            class="margin-right--small"
            on={{
              click: () => {
                this.setShowingSelectRepoModal(true);
              }
            }}
          >
            Set Project Repo
          </b-button>
          <b-form-input value={this.getProjectRepo()} disabled />
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
          </div>
        </div>
      </Loading>
    );
  }

  public async mounted() {
    await this.listReposForUser();
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
        {this.renderSelectRepoModal()}
      </div>
    );
  }
}
