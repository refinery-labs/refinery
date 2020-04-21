import { VuexModule, Module, Mutation, Action } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { listGithubReposForUser } from '@/store/fetchers/api-helpers';
import { GithubRepo } from '@/types/api-types';

// This is the name that this will be added to the Vuex store with.
// You will need to add to the `RootState` interface if you want to access this state via `rootState` from anywhere.
const storeName = StoreType.projectSettings;

export interface ProjectSettingsState {
  reposForUser?: GithubRepo[] | null;
  selectedRepo: GithubRepo | null;
}

export const baseState: ProjectSettingsState = {
  reposForUser: null,
  selectedRepo: null
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: storeName })
export class ProjectSettingsStore extends VuexModule<ThisType<ProjectSettingsState>, RootState>
  implements ProjectSettingsState {
  public reposForUser?: GithubRepo[] | null = initialState.reposForUser;
  public selectedRepo: GithubRepo | null = initialState.selectedRepo;

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public async setReposForUser(reposForUser: GithubRepo[] | null) {
    this.reposForUser = reposForUser;
  }

  @Mutation
  public async setSelectedRepo(repo: GithubRepo) {
    this.selectedRepo = repo;
  }

  @Action
  public async listReposForUser(): Promise<void> {
    if (!this.reposForUser) {
      const userRepos = await listGithubReposForUser();
      if (!userRepos) {
        return;
      }

      if (!this.context.rootState.project.openedProjectConfig) {
        throw new Error('no project config open');
      }

      const configuredRepo = this.context.rootState.project.openedProjectConfig.project_repo;

      const configuredUserRepo = userRepos.find(repo => repo.clone_url === configuredRepo);
      if (!configuredUserRepo) {
        // unable to find configured repo in list, maybe also throw an error?
        this.setReposForUser(userRepos);
      } else {
        const userReposWithoutConfiguredRepo = userRepos.filter(repo => repo.clone_url !== configuredRepo);

        // put the already configured repo first
        this.setReposForUser([configuredUserRepo, ...userReposWithoutConfiguredRepo]);
        this.setSelectedRepo(configuredUserRepo);
      }
    }
  }
}
