import { namespace } from 'vuex-class';
import Component from 'vue-class-component';
import Vue from 'vue';
import { GithubRepo } from '@/types/api-types';
import { getFriendlyDurationSinceString } from '@/utils/time-utils';
import { LoadingContainerProps } from '@/types/component-types';
import Loading from '@/components/Common/Loading.vue';
import { RepoSelectionModalStore } from '@/store/modules/modals/repo-selection-modal';
import { RepoSelectionModalStoreModule } from '@/store';
import { ProjectConfig, RefineryProject } from '@/types/graph';

const project = namespace('project');

@Component
export default class RepoSelectionModal extends Vue {
  @project.State openedProject!: RefineryProject | null;
  @project.State openedProjectConfig!: ProjectConfig | null;

  private repoSearch: string = '';

  @project.Action setProjectConfigRepo!: (projectConfigRepo: string | undefined) => void;

  private async setShowingSelectRepoModal(showing: boolean): Promise<void> {
    await RepoSelectionModalStoreModule.setRepoSelectionModalVisible(showing);
    if (!showing) {
      await RepoSelectionModalStoreModule.reorganizeUserRepos();
    }
  }

  private setRepoSearch(search: string) {
    this.repoSearch = search;
  }

  private async setProjectRepoAndClose() {
    if (RepoSelectionModalStoreModule.selectedRepo) {
      await this.setProjectConfigRepo(RepoSelectionModalStoreModule.selectedRepo.clone_url);
    }
    await this.setShowingSelectRepoModal(false);
  }

  private async removeProjectRepoAndClose() {
    await this.setProjectConfigRepo(undefined);
    await this.setShowingSelectRepoModal(false);
  }

  private async createNewUserRepoAndClose() {
    await RepoSelectionModalStoreModule.createNewUserRepo();
    await this.setShowingSelectRepoModal(false);
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

    const showingDetails =
      RepoSelectionModalStoreModule.selectedRepo &&
      RepoSelectionModalStoreModule.selectedRepo.full_name === repo.full_name;
    const lastUpdatedTime = getFriendlyDurationSinceString(Date.parse(repo.updated_at));

    return (
      <b-card
        no-body
        class="mb-1"
        bg-variant={showingDetails ? 'light' : 'default'}
        on={{ click: async () => await RepoSelectionModalStoreModule.setSelectedRepo(repo) }}
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
    if (RepoSelectionModalStoreModule.reposForUser === undefined) {
      return <p>Loading user's repos...</p>;
    }

    if (RepoSelectionModalStoreModule.reposForUser === null) {
      return <p>There was an error when getting user's repos.</p>;
    }

    const searchRepoNames = (repo: GithubRepo) => {
      return repo.full_name.toLowerCase().includes(this.repoSearch.toLowerCase());
    };

    return (
      <div role="tablist" class="set-project-repo">
        {RepoSelectionModalStoreModule.reposForUser.filter(searchRepoNames).map(this.renderUserRepoItem)}
      </div>
    );
  }

  private render() {
    const modalOnHandlers = {
      hidden: () => this.setShowingSelectRepoModal(false)
    };

    const createNewRepoProps: LoadingContainerProps = {
      label: RepoSelectionModalStoreModule.createNewRepoStateLabel,
      show: RepoSelectionModalStoreModule.isCreatingNewRepo
    };

    return (
      <b-modal
        on={modalOnHandlers}
        ok-variant="danger"
        footer-class="p-2"
        ref="console-modal"
        hide-footer
        title="Select Project Repo"
        visible={RepoSelectionModalStoreModule.visible}
      >
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
                  value={RepoSelectionModalStoreModule.newRepoName}
                  on={{ input: RepoSelectionModalStoreModule.setNewRepoName }}
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
                  value={RepoSelectionModalStoreModule.newRepoDescription}
                  on={{ input: RepoSelectionModalStoreModule.setNewRepoDescription }}
                />
              </div>
              <div class="text-align--right margin-top--normal">
                <b-button
                  variant="primary"
                  disabled={RepoSelectionModalStoreModule.isCreatingNewRepo}
                  on={{ click: this.createNewUserRepoAndClose }}
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
            <div class="text-align--center margin-top--normal">
              <b-button variant="danger" on={{ click: this.removeProjectRepoAndClose }}>
                Clear repo for project
              </b-button>
            </div>
          </b-tab>
        </b-tabs>
      </b-modal>
    );
  }
}
