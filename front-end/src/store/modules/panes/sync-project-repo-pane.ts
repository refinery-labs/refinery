import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { ProjectViewActions, ProjectViewMutators } from '@/constants/store-constants';
import { OpenProjectMutation } from '@/types/project-editor-types';
import { ProjectConfig, RefineryProject } from '@/types/graph';
import { StatusRow } from 'isomorphic-git';
import { newBranchText } from '@/constants/project-editor-constants';
import { getStatusForFileInfo, RepoCompilationError } from '@/repo-compiler/lib/git-utils';
import { GitClient } from '@/repo-compiler/lib/git-client';
import { loadProjectFromDir } from '@/repo-compiler/one-to-one/git-to-refinery';
import uuid from 'uuid';
import { GitDiffInfo, GitStatusResult, InvalidGitRepoError } from '@/repo-compiler/lib/git-types';
import { REFINERY_COMMIT_AUTHOR_NAME } from '@/repo-compiler/shared/constants';
import { GitStoreModule } from '@/store';
import git from 'isomorphic-git';
import { http } from '@/repo-compiler/lib/git-http';

const storeName = StoreType.syncProjectRepo;

export enum GitPushResult {
  Success = 'Success',
  UnableToFastForward = 'UnableToFastForward',
  Other = 'Other'
}

const gitPushResultToMessage: Record<GitPushResult, string> = {
  [GitPushResult.Success]: `${REFINERY_COMMIT_AUTHOR_NAME} successfully pushed to the remote branch.`,
  [GitPushResult.UnableToFastForward]:
    'Unable to fast forward, you can force push your project to your remote branch, overwriting any remote changes.',
  [GitPushResult.Other]:
    'Some unknown git push error has occurred. If you continue to have this problem, please reach out to the Refinery team.'
};

// Types
export interface SyncProjectRepoPaneState {
  remoteBranchName: string;
  creatingNewBranch: boolean;
  gitStatusResult: Array<StatusRow>;
  repoBranches: string[];
  pushingToRepo: boolean;
  commitMessage: string;
  projectSessionId: string | null;
  currentlyDiffedFile: string | null;

  repoCompilationError?: RepoCompilationError;
  gitPushResult?: GitPushResult;
}

// Initial State
const moduleState: SyncProjectRepoPaneState = {
  remoteBranchName: 'master',
  creatingNewBranch: false,
  gitStatusResult: [],
  repoBranches: [],
  pushingToRepo: false,
  commitMessage: 'update project from Refinery UI',
  projectSessionId: null,
  currentlyDiffedFile: null,

  repoCompilationError: undefined,
  gitPushResult: undefined
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, name: storeName })
export class SyncProjectRepoPaneStore extends VuexModule<ThisType<SyncProjectRepoPaneState>, RootState>
  implements SyncProjectRepoPaneState {
  public remoteBranchName: string = initialState.remoteBranchName;
  public creatingNewBranch: boolean = initialState.creatingNewBranch;
  public gitStatusResult: Array<StatusRow> = initialState.gitStatusResult;
  public repoBranches: string[] = initialState.repoBranches;
  public pushingToRepo: boolean = initialState.pushingToRepo;
  public commitMessage: string = initialState.commitMessage;
  public projectSessionId: string | null = initialState.projectSessionId;
  public currentlyDiffedFile: string | null = initialState.currentlyDiffedFile;

  public repoCompilationError?: RepoCompilationError = initialState.repoCompilationError;
  public gitPushResult?: GitPushResult = initialState.gitPushResult;

  @Mutation
  public resetState() {
    if (this.projectSessionId !== null) {
      // TODO: Remove this once we get rid of the unique projectSessionId
      GitStoreModule.deleteProjectFromCache(this.projectSessionId);
    }

    resetStoreState(this, initialState);
  }

  get getRemoteBranchName(): string {
    return this.remoteBranchName !== newBranchText ? this.remoteBranchName : '';
  }

  get getGitPushResultMessage(): string {
    if (!this.gitPushResult) return 'No git push has been made yet';

    return gitPushResultToMessage[this.gitPushResult];
  }

  get getGitPushResult(): GitPushResult | undefined {
    return this.gitPushResult;
  }

  get getGitStatusStats(): GitStatusResult {
    return this.gitStatusResult.reduce(
      (statusStats, fileRow) => {
        const statsForFile = getStatusForFileInfo(fileRow);
        return {
          newFiles: statusStats.newFiles + statsForFile.newFiles,
          modifiedFiles: statusStats.modifiedFiles + statsForFile.modifiedFiles,
          deletedFiles: statusStats.deletedFiles + statsForFile.deletedFiles
        };
      },
      { newFiles: 0, modifiedFiles: 0, deletedFiles: 0 } as GitStatusResult
    );
  }

  get isPushingToRepo(): boolean {
    return this.pushingToRepo;
  }

  get getCurrentlyDiffedFile(): string | null {
    return this.currentlyDiffedFile;
  }

  @Mutation
  public async setRemoteBranchName(remoteBranchName: string) {
    this.creatingNewBranch = false;
    this.remoteBranchName = remoteBranchName;
  }

  @Mutation
  public async setNewRemoteBranchName(remoteBranchName: string) {
    this.creatingNewBranch = true;
    this.remoteBranchName = remoteBranchName;
  }

  @Mutation
  public async setIsCreatingNewBranch(creatingNewBranch: boolean) {
    this.creatingNewBranch = creatingNewBranch;
  }

  @Mutation
  public async setGitStatusResult(gitStatusResult: Array<StatusRow>) {
    this.gitStatusResult = gitStatusResult;
  }

  @Mutation
  public async setGitPushResult(gitPushResult: GitPushResult | undefined) {
    this.gitPushResult = gitPushResult;
  }

  @Mutation
  public async setRepoBranches(repoBranches: string[]) {
    this.repoBranches = repoBranches;
  }

  @Mutation
  public async clearGitPushResult() {
    this.gitPushResult = undefined;
  }

  @Mutation
  public async clearGitStatusResult() {
    this.gitStatusResult = [];
    this.currentlyDiffedFile = null;
  }

  @Mutation
  public async setPushingToRepo(pushingToRepo: boolean) {
    this.pushingToRepo = pushingToRepo;
  }

  @Mutation
  public async setCurrentlyDiffedFile(currentlyDiffedFile: string | null) {
    this.currentlyDiffedFile = currentlyDiffedFile;
  }

  @Mutation
  public async setCommitMessage(commitMessage: string) {
    this.commitMessage = commitMessage;
  }

  @Mutation
  public async setRepoCompilationError(repoCompilationError: RepoCompilationError) {
    this.repoCompilationError = repoCompilationError;
  }

  @Mutation
  public async setRandomSessionProjectId(projectID: string) {
    this.projectSessionId = projectID;
  }

  @Action
  public getOpenedProject(): RefineryProject {
    if (!this.context.rootState.project.openedProject) {
      throw new Error('no project open');
    }
    return this.context.rootState.project.openedProject;
  }

  @Action
  public getOpenedProjectConfig(): ProjectConfig {
    if (!this.context.rootState.project.openedProjectConfig) {
      throw new Error('no project config open');
    }
    return this.context.rootState.project.openedProjectConfig;
  }

  @Action
  public async pushToRepo(force: boolean) {
    if (this.projectSessionId === null) {
      const msg = 'Cannot push to repo with missing project session id';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }

    await this.setPushingToRepo(true);

    const gitClient = GitStoreModule.getGitClientByProjectId(this.projectSessionId);
    const gitActionHandler = GitStoreModule.getRefineryGitActionHandler(this.projectSessionId);

    const result = await gitActionHandler.stageFilesAndPushToRemote(
      this.gitStatusResult,
      this.remoteBranchName,
      this.commitMessage,
      force
    );

    await this.setGitPushResult(result);
    await this.setPushingToRepo(false);

    if (result !== GitPushResult.Success) {
      // git push did not succeed
      // if (result !== GitPushResult.UnableToFastForward) {
      return;
      // }
      //
      // await git.pull({
      //   fs: gitClient.fs,
      //   dir: gitClient.dir,
      //   http,
      //   ref: this.remoteBranchName
      // });
      //
      // await git.merge({
      //   fs: gitClient.fs,
      //   dir: gitClient.dir,
      //
      // });
    }

    // git push succeeded
    const params: OpenProjectMutation = {
      project: this.context.rootState.project.openedProject,
      config: this.context.rootState.project.openedProjectConfig,
      markAsDirty: false
    };
    await this.context.dispatch(`project/${ProjectViewActions.updateProject}`, params, { root: true });

    await this.clearGitPushResult();
    await this.clearGitStatusResult();

    // we have just pushed successfully, the current branch will have no changes
    await this.setGitStatusResult([]);
  }

  @Action
  public async forcePushToRemoteBranch() {
    await this.pushToRepo(true);
  }

  @Action
  public async pushToRemoteBranch() {
    await this.pushToRepo(false);
  }

  @Action
  public async diffCompiledProject(): Promise<GitDiffInfo> {
    if (this.projectSessionId === null) {
      const msg = 'Cannot diff repo with missing project session id';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }

    // Force a save of the currently selected resource
    await this.context.dispatch(`project/${ProjectViewActions.saveSelectedResource}`, true, { root: true });

    const gitClient = GitStoreModule.getGitClientByProjectId(this.projectSessionId);
    const gitActionHandler = GitStoreModule.getRefineryGitActionHandler(this.projectSessionId);

    await this.clearGitPushResult();

    const project = await this.getOpenedProject();

    if (!this.repoBranches.includes(this.remoteBranchName)) {
      try {
        await git.branch({
          fs: gitClient.fs,
          dir: gitClient.dir,
          ref: this.remoteBranchName
        });
        await gitClient.checkout({
          ref: this.remoteBranchName,
          force: true
        });
      } catch (e) {
        console.error('branch error:', e);
      }
      // return {
      //   originalFiles: {},
      //   changedFiles: {}
      // };
    } else {
      // TODO: See if we can move this logic into the Action handler to avoid breaking the Git abstraction
      await gitClient.checkout({
        ref: this.remoteBranchName,
        force: true
      });
    }
    await gitActionHandler.writeProjectToDisk(project);

    // get list of files that were changed
    const statusResult = await gitClient.status();
    await this.setGitStatusResult(statusResult);

    // get contents from changed files before and after they were modified
    // TODO this call will force checkout and compile the project again, there might be a way to optimize this
    return await gitActionHandler.getDiffFileInfo(project, this.remoteBranchName, this.gitStatusResult);
  }

  @Action
  public async compileClonedProject(gitClient: GitClient): Promise<RefineryProject | null> {
    if (this.projectSessionId === null) {
      const msg = 'Cannot compile clone repo with missing project session id';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }

    try {
      return await loadProjectFromDir(gitClient.fs, this.projectSessionId, gitClient.dir);
    } catch (e) {
      if (e instanceof RepoCompilationError) {
        // await this.setRepoCompilationError(e);
      }
      return this.context.rootState.project.openedProject;
    }
  }

  @Action
  public async setupLocalProjectRepo(projectConfig: ProjectConfig) {
    if (!projectConfig.project_repo) {
      const msg = 'Unable to setup local project repo with missing git repo URI';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }

    const projectSessionId = uuid.v4();

    await this.setRandomSessionProjectId(projectSessionId);

    GitStoreModule.createGitStore({
      projectId: projectSessionId,
      repoUri: projectConfig.project_repo
    });

    const gitClient = GitStoreModule.getGitClientByProjectId(projectSessionId);

    await gitClient.clone();

    const currentBranch = await gitClient.currentBranch();
    if (currentBranch) {
      await this.setRemoteBranchName(currentBranch);
    }

    const repoBranches = await gitClient.listBranches({ remote: 'origin' });
    await this.setRepoBranches(repoBranches);

    const compiledProject = await this.compileClonedProject(gitClient);
    if (!compiledProject) {
      return;
    }

    const config = this.context.rootState.project.openedProjectConfig;

    const params: OpenProjectMutation = {
      project: compiledProject,
      config: config,
      markAsDirty: false
    };

    await this.context.dispatch(`project/${ProjectViewActions.updateProject}`, params, { root: true });
  }
}
