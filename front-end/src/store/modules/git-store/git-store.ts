import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { GitClient } from '@/repo-compiler/lib/git-client';
import LightningFS from '@isomorphic-git/lightning-fs';
import { PromiseFsClient } from 'isomorphic-git';
import { InvalidGitStoreState } from '@/store/modules/git-store/types';
import { RefineryGitActionHandler } from '@/repo-compiler/shared/refinery-git-action-handler';
import { removeKeyFromObject } from '@/lib/funtional-extensions';

export interface GitProjectConfig {
  repoUri: string;
  projectId: string;
}

export type ProjectToGitRepoLookup = {
  [key: string]: GitProjectConfig;
};

export interface GitState {
  projectIdToGitConfigLookup: ProjectToGitRepoLookup;
}

export const baseState: GitState = {
  projectIdToGitConfigLookup: {}
};

const initialState = deepJSONCopy(baseState);

type ClientLookup<T> = {
  [key: string]: T;
};

/**
 * Holds instances of the File System (FS) object, where each FS is associated with a given repo.
 */
let fsInstanceCache: ClientLookup<PromiseFsClient> = {};

/**
 * Holds instances of the GitClient, which are created per project (but they share a FS instance if projects share a repo).
 */
let gitClientCache: ClientLookup<GitClient> = {};

/**
 * Holds instances of RefineryGitActionHandler instances, which are wrappers around GitClients.
 * We do this so that Refinery logic can be abstracted from the Git implementation itself.
 */
let refineryGitActionHandlerCache: ClientLookup<RefineryGitActionHandler> = {};

function getOrCreateFsInstance(repoUri: string, resetFS: boolean = false) {
  if (fsInstanceCache[repoUri]) {
    return fsInstanceCache[repoUri];
  }

  // If we do ever want to wipe, it might make sense to just `rmdir` a project's folder specifically.
  const fs = new LightningFS('project', {
    wipe: resetFS === undefined ? false : resetFS
  });

  fsInstanceCache[repoUri] = fs;

  return fs;
}

function generateCacheKey(config: GitProjectConfig) {
  return JSON.stringify(config);
}

@Module({ namespaced: true, name: StoreType.git })
export class GitStore extends VuexModule<ThisType<GitState>, RootState> implements GitState {
  /**
   * This is used to easily associate a project's ID with a git config (which can be used to get the Git client).
   */
  public projectIdToGitConfigLookup: ProjectToGitRepoLookup = initialState.projectIdToGitConfigLookup;

  get getGitClientByProjectId() {
    return (projectId: string) => {
      const gitConfig = this.projectIdToGitConfigLookup[projectId];

      if (!gitConfig) {
        // return null;
        throw new InvalidGitStoreState('Attempted to read a git client before it was initialized');
      }

      const clientCacheKey = generateCacheKey(gitConfig);

      if (gitClientCache[clientCacheKey]) {
        return gitClientCache[clientCacheKey];
      }

      throw new InvalidGitStoreState('Git client exists in lookup but not in the cache');
    };
  }

  get getRefineryGitActionHandler() {
    return (projectId: string) => {
      const gitConfig = this.projectIdToGitConfigLookup[projectId];

      if (!gitConfig) {
        throw new InvalidGitStoreState('Attempted to read a refinery git action client before it was initialized');
      }

      const clientCacheKey = generateCacheKey(gitConfig);

      if (refineryGitActionHandlerCache[clientCacheKey]) {
        return refineryGitActionHandlerCache[clientCacheKey];
      }

      throw new InvalidGitStoreState('Refinery git action client exists in lookup but not in the cache');
    };
  }

  @Mutation
  public resetState() {
    fsInstanceCache = {};
    gitClientCache = {};
    refineryGitActionHandlerCache = {};

    resetStoreState(this, baseState);
  }

  @Mutation
  private removeProjectFromLookup(projectId: string) {
    this.projectIdToGitConfigLookup = removeKeyFromObject(this.projectIdToGitConfigLookup, projectId);
  }

  @Action
  public async deleteProjectFromCache(projectId: string) {
    const gitConfig = this.projectIdToGitConfigLookup[projectId];

    const clientCacheKey = generateCacheKey(gitConfig);

    const gitClient = gitClientCache[clientCacheKey];

    // Clear clients leftover
    delete gitClientCache[clientCacheKey];
    delete refineryGitActionHandlerCache[clientCacheKey];

    const fs = fsInstanceCache[gitConfig.repoUri];

    // Nuke the folder where the project was checked out to
    await fs.promises.rmdir(gitClient.dir);
  }

  @Mutation
  public createGitStore(config: GitProjectConfig) {
    const gitClientCacheKey = generateCacheKey(config);

    const fs = getOrCreateFsInstance(config.repoUri);

    const dir = `/projects/${config.projectId}`;

    const gitClient = new GitClient(config.repoUri, fs, dir);

    gitClientCache[gitClientCacheKey] = gitClient;

    refineryGitActionHandlerCache[gitClientCacheKey] = new RefineryGitActionHandler(gitClient);

    this.projectIdToGitConfigLookup = {
      ...this.projectIdToGitConfigLookup,
      [config.projectId]: config
    };
  }

  @Action
  public setExampleViaAction(value: string) {
    // this.setExample(value);
  }
}
