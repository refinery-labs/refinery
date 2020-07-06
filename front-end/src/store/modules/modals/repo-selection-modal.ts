// This is the name that this will be added to the Vuex store with.
// You will need to add to the `RootState` interface if you want to access this state via `rootState` from anywhere.
import { RootState, StoreType } from '@/store/store-types';
import { GithubRepo } from '@/types/api-types';
import { NewGitRepoStateType } from '@/types/project-settings-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { newGitRepoStateToLabel } from '@/constants/project-settings-constants';
import { resetStoreState } from '@/utils/store-utils';
import { LoggingAction } from '@/lib/LoggingMutation';
import { createNewRepoForUser, listGithubReposForUser } from '@/store/fetchers/api-helpers';
import { createToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';
import { ProjectViewActions } from '@/constants/store-constants';
import { SyncProjectRepoPaneStoreModule } from '@/store';

const storeName = StoreType.repoSelectionModal;

export interface RepoSelectionModalState {
  visible: boolean;
  reposForUser?: GithubRepo[] | null;
  selectedRepo: GithubRepo | null;
  newRepoName: string;
  newRepoDescription: string;
  creatingRepoState: NewGitRepoStateType;
}

export const baseState: RepoSelectionModalState = {
  visible: false,
  reposForUser: null,
  selectedRepo: null,
  newRepoName: '',
  newRepoDescription: '',
  creatingRepoState: NewGitRepoStateType.REPO_NOT_CREATED
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: storeName })
export class RepoSelectionModalStore extends VuexModule<ThisType<RepoSelectionModalState>, RootState>
  implements RepoSelectionModalState {
  public visible: boolean = initialState.visible;
  public reposForUser?: GithubRepo[] | null = initialState.reposForUser;
  public selectedRepo: GithubRepo | null = initialState.selectedRepo;
  public newRepoName: string = initialState.newRepoName;
  public newRepoDescription: string = initialState.newRepoDescription;
  public creatingRepoState: NewGitRepoStateType = initialState.creatingRepoState;

  get isCreatingNewRepo(): boolean {
    return (
      this.creatingRepoState === NewGitRepoStateType.REPO_CREATED ||
      this.creatingRepoState === NewGitRepoStateType.PROJECT_COMPILED
    );
  }

  get hasCreatedNewRepo(): boolean {
    return this.creatingRepoState === NewGitRepoStateType.PROJECT_PUSHED;
  }

  get createNewRepoStateLabel(): string {
    return newGitRepoStateToLabel[this.creatingRepoState];
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public async setRepoSelectionModalVisible(visible: boolean) {
    this.visible = visible;
  }

  @Mutation
  public async setReposForUser(reposForUser: GithubRepo[] | null) {
    this.reposForUser = reposForUser;
  }

  @Mutation
  public async setSelectedRepo(repo: GithubRepo) {
    this.selectedRepo = repo;
  }

  @Mutation
  public async setNewRepoName(newRepoName: string) {
    this.newRepoName = newRepoName;
  }

  @Mutation
  public async setNewRepoDescription(newRepoDescription: string) {
    this.newRepoDescription = newRepoDescription;
  }

  @Mutation
  public async setCreatingRepoState(creatingRepoState: NewGitRepoStateType) {
    this.creatingRepoState = creatingRepoState;
  }

  @Mutation
  public async resetCreatingRepoState() {
    this.creatingRepoState = NewGitRepoStateType.REPO_NOT_CREATED;
  }

  @LoggingAction
  public async reorganizeUserRepos() {
    if (this.reposForUser) {
      await this.setUserRepos(this.reposForUser);
    }
  }

  @LoggingAction
  public async setUserRepos(userRepos: GithubRepo[]) {
    if (!this.context.rootState.project.openedProjectConfig) {
      throw new Error('no project config open');
    }

    const configuredRepo = this.context.rootState.project.openedProjectConfig.project_repo;

    const configuredUserRepo = userRepos.find(repo => repo.clone_url === configuredRepo);
    if (!configuredUserRepo) {
      // unable to find configured repo in list, maybe also throw an error?
      await this.setReposForUser(userRepos);
      return;
    }

    const userReposWithoutConfiguredRepo = userRepos.filter(repo => repo.clone_url !== configuredRepo);

    // put the already configured repo first
    await this.setReposForUser([configuredUserRepo, ...userReposWithoutConfiguredRepo]);
    await this.setSelectedRepo(configuredUserRepo);
  }

  @LoggingAction
  public async cacheReposForUser(): Promise<void> {
    if (!this.reposForUser) {
      const userRepos = await listGithubReposForUser();
      if (!userRepos) {
        return;
      }
      await this.setUserRepos(userRepos);
    }
  }

  @LoggingAction
  public async createNewUserRepo(): Promise<void> {
    this.setCreatingRepoState(NewGitRepoStateType.REPO_NOT_CREATED);

    const newRepo = await createNewRepoForUser(this.newRepoName, this.newRepoDescription);

    this.setCreatingRepoState(NewGitRepoStateType.REPO_CREATED);

    if (!newRepo) {
      await createToast(this.context.dispatch, {
        title: 'Failed to Create New Repository',
        content:
          'Unable to create a new repository right now. If the problem persists, reach out to the Refinery team.',
        variant: ToastVariant.danger,
        autoHideDelay: 7000
      });
      this.resetCreatingRepoState();
      return;
    }

    await this.setSelectedRepo(newRepo);

    await this.context.dispatch(`project/${ProjectViewActions.setProjectConfigRepo}`, newRepo.clone_url, {
      root: true
    });

    this.setCreatingRepoState(NewGitRepoStateType.PROJECT_COMPILED);

    await SyncProjectRepoPaneStoreModule.pushToRemoteBranch();

    this.setCreatingRepoState(NewGitRepoStateType.PROJECT_PUSHED);
  }
}
