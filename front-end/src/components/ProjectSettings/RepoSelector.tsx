import { namespace } from 'vuex-class';
import Component from 'vue-class-component';
import Vue from 'vue';
import { GithubRepo, SavedBlockSearchResult } from '@/types/api-types';
import { getFriendlyDurationSinceString } from '@/utils/time-utils';
import { LoadingContainerProps } from '@/types/component-types';
import Loading from '@/components/Common/Loading.vue';
import { RepoSelectorStoreModule } from '@/store';
import { ProjectConfig, RefineryProject } from '@/types/graph';
import { Prop } from 'vue-property-decorator';

const project = namespace('project');

export interface RepoSelectorProps {
  selectedRepoCallback: () => void;
  showClearRepoButton?: boolean;
}

@Component
export default class RepoSelector extends Vue implements RepoSelectorProps {
  @Prop({ required: true }) selectedRepoCallback!: () => void;
  @Prop({ required: true, default: true }) showClearRepoButton!: boolean;

  @project.State openedProject!: RefineryProject | null;
  @project.State openedProjectConfig!: ProjectConfig | null;

  private repoSearch: string = '';

  @project.Action setProjectConfigRepo!: (projectConfigRepo: string | undefined) => void;

  private setRepoSearch(search: string) {
    this.repoSearch = search;
  }

  private async setProjectRepo() {
    if (RepoSelectorStoreModule.selectedRepo) {
      await this.setProjectConfigRepo(RepoSelectorStoreModule.selectedRepo.clone_url);
    }
    await this.selectedRepoCallback();
  }

  private async removeProjectRepo() {
    await this.setProjectConfigRepo(undefined);
    await this.selectedRepoCallback();
  }

  private async createNewUserRepo() {
    await RepoSelectorStoreModule.createNewUserRepo();
    await this.selectedRepoCallback();
  }

  private getCurrentlyConfiguredRepoURL(): string | null {
    if (!this.openedProjectConfig || !this.openedProjectConfig.project_repo) {
      return null;
    }
    return this.openedProjectConfig.project_repo;
  }

  private renderUserRepoItem(repo: GithubRepo) {
    const privateRepoBadge = repo.private ? (
      <b-badge pill={false} class="margin-right--small">
        Private
      </b-badge>
    ) : null;

    const currentRepoURL = this.getCurrentlyConfiguredRepoURL();
    const isCurrentlyConfiguredRepo = currentRepoURL && currentRepoURL === repo.clone_url;
    const currentConfiguredRepoBadge = isCurrentlyConfiguredRepo ? (
      <b-badge pill={false} variant="primary" class="margin-right--small">
        Current
      </b-badge>
    ) : null;

    const showingDetails =
      RepoSelectorStoreModule.selectedRepo && RepoSelectorStoreModule.selectedRepo.full_name === repo.full_name;
    const lastUpdatedTime = getFriendlyDurationSinceString(Date.parse(repo.updated_at));

    return (
      <b-card
        no-body
        class="mb-1"
        bg-variant={showingDetails ? 'light' : 'default'}
        on={{ click: async () => await RepoSelectorStoreModule.setSelectedRepo(repo) }}
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
              <b-button variant="primary" on={{ click: this.setProjectRepo }}>
                Set repo for project
              </b-button>
            </div>
          </b-card-body>
        </b-collapse>
      </b-card>
    );
  }

  private renderUserRepos() {
    if (RepoSelectorStoreModule.reposForUser === undefined) {
      return <p>Loading user's repos...</p>;
    }

    if (RepoSelectorStoreModule.reposForUser === null) {
      return <p>There was an error when getting user's repos.</p>;
    }

    const searchRepoNames = (repo: GithubRepo) => {
      return repo.full_name.toLowerCase().includes(this.repoSearch.toLowerCase());
    };

    return (
      <div role="tablist" class="set-project-repo">
        {RepoSelectorStoreModule.reposForUser.filter(searchRepoNames).map(this.renderUserRepoItem)}
      </div>
    );
  }

  private renderClearRepoButton() {
    if (this.showClearRepoButton) {
      return (
        <div class="text-align--center margin-top--normal">
          <b-button variant="danger" on={{ click: this.removeProjectRepo }}>
            Clear repo for project
          </b-button>
        </div>
      );
    }
    return null;
  }

  private render() {
    const createNewRepoProps: LoadingContainerProps = {
      label: RepoSelectorStoreModule.createNewRepoStateLabel,
      show: RepoSelectorStoreModule.isCreatingNewRepo
    };

    return (
      <b-tabs>
        <b-tab title="Create New Repo">
          <Loading props={createNewRepoProps}>
            <div>
              <label class="d-block" htmlFor="new-repository-name-input">
                Name
              </label>
              <b-form-input
                id="new-repository-name-input"
                className="margin-bottom--normal"
                placeholder="Name of new repository"
                value={RepoSelectorStoreModule.newRepoName}
                on={{ input: RepoSelectorStoreModule.setNewRepoName }}
              />
            </div>
            <div class="margin-top--normal">
              <label class="d-block" htmlFor="new-repository-description-input">
                Description
              </label>
              <b-form-input
                id="new-repository-description-input"
                className="margin-bottom--normal"
                placeholder="Description for new repository"
                value={RepoSelectorStoreModule.newRepoDescription}
                on={{ input: RepoSelectorStoreModule.setNewRepoDescription }}
              />
            </div>
            <div class="text-align--right margin-top--normal">
              <b-button
                variant="primary"
                disabled={RepoSelectorStoreModule.isCreatingNewRepo}
                on={{ click: this.createNewUserRepo }}
              >
                Create new user repo
              </b-button>
            </div>
          </Loading>
        </b-tab>
        <b-tab title="Use Existing Repo">
          <b-form-input
            className="margin-bottom--normal"
            placeholder="Search for repo..."
            value={this.repoSearch}
            on={{ input: this.setRepoSearch }}
          />
          {this.renderUserRepos()}
          {this.renderClearRepoButton()}
        </b-tab>
      </b-tabs>
    );
  }
}
