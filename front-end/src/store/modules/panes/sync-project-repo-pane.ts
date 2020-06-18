import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { ProjectViewActions } from '@/constants/store-constants';
import { OpenProjectMutation } from '@/types/project-editor-types';
import { ProjectConfig, RefineryProject } from '@/types/graph';
import { StatusRow } from 'isomorphic-git';
import { getStatusForFileInfo, getStatusMessageForFileInfo, RepoCompilationError } from '@/repo-compiler/lib/git-utils';
import { GitClient } from '@/repo-compiler/lib/git-client';
import { loadProjectFromDir } from '@/repo-compiler/one-to-one/git-to-refinery';
import uuid from 'uuid';
import { GitDiffInfo, GitStatusResult, InvalidGitRepoError } from '@/repo-compiler/lib/git-types';
import { REFINERY_COMMIT_AUTHOR_NAME } from '@/repo-compiler/shared/constants';
import { GitStoreModule } from '@/store';
import { LoggingAction } from '@/lib/LoggingMutation';

const storeName = StoreType.syncProjectRepo;

export enum GitPushResult {
  Success = 'Success',
  UnableToFastForward = 'UnableToFastForward',
  Other = 'Other'
}

type GitPushResultMessageLookup = {
  [key in GitPushResult]: string;
};

const gitPushResultToMessage: GitPushResultMessageLookup = {
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
  viewingProjectId: string | null;
  currentlyDiffedFile: string | null;
  gitDiffInfo: GitDiffInfo;

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
  viewingProjectId: null,
  currentlyDiffedFile: null,
  gitDiffInfo: { originalFiles: {}, changedFiles: {} },

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
  public viewingProjectId: string | null = initialState.viewingProjectId;
  public currentlyDiffedFile: string | null = initialState.currentlyDiffedFile;
  public gitDiffInfo: GitDiffInfo = initialState.gitDiffInfo;

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
    return this.remoteBranchName;
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
  public setRemoteBranchName(remoteBranchName: string) {
    this.remoteBranchName = remoteBranchName;
  }

  @Mutation
  public setNewRemoteBranchName(remoteBranchName: string) {
    this.remoteBranchName = remoteBranchName;
  }

  @Mutation
  public setCreatingNewBranch(creatingNewBranch: boolean) {
    this.creatingNewBranch = creatingNewBranch;
  }

  @Mutation
  public setGitStatusResult(gitStatusResult: Array<StatusRow>) {
    this.gitStatusResult = gitStatusResult;
  }

  @Mutation
  public setGitPushResult(gitPushResult: GitPushResult | undefined) {
    this.gitPushResult = gitPushResult;
  }

  @Mutation
  public setGitDiffInfo(gitDiffInfo: GitDiffInfo) {
    this.gitDiffInfo = gitDiffInfo;
  }

  @Mutation
  public setRepoBranches(repoBranches: string[]) {
    this.repoBranches = repoBranches;
  }

  @Mutation
  public clearGitPushResult() {
    this.gitPushResult = undefined;
  }

  @Mutation
  public clearGitStatusResult() {
    this.gitStatusResult = [];
    this.currentlyDiffedFile = null;
  }

  @Mutation
  public setPushingToRepo(pushingToRepo: boolean) {
    this.pushingToRepo = pushingToRepo;
  }

  @Mutation
  public setCurrentlyDiffedFile(currentlyDiffedFile: string | null) {
    this.currentlyDiffedFile = currentlyDiffedFile;
  }

  @Mutation
  public setCommitMessage(commitMessage: string) {
    this.commitMessage = commitMessage;
  }

  @Mutation
  public setRepoCompilationError(repoCompilationError: RepoCompilationError) {
    this.repoCompilationError = repoCompilationError;
  }

  @Mutation
  public setRandomSessionProjectId(projectID: string) {
    this.projectSessionId = projectID;
  }

  @Mutation
  public setViewingProjectId(projectID: string) {
    this.viewingProjectId = projectID;
  }

  @LoggingAction
  public getOpenedProject(): RefineryProject {
    if (!this.context.rootState.project.openedProject) {
      throw new Error('no project open');
    }
    return this.context.rootState.project.openedProject;
  }

  @LoggingAction
  public getOpenedProjectConfig(): ProjectConfig {
    if (!this.context.rootState.project.openedProjectConfig) {
      throw new Error('no project config open');
    }
    return this.context.rootState.project.openedProjectConfig;
  }

  @LoggingAction
  public async pushToRepo(force: boolean) {
    if (this.projectSessionId === null) {
      const msg = 'Cannot push to repo with missing project session id';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }

    this.setPushingToRepo(true);

    const gitClient = GitStoreModule.getGitClientByProjectId(this.projectSessionId);
    const gitActionHandler = GitStoreModule.getRefineryGitActionHandler(this.projectSessionId);

    const result = await gitActionHandler.stageFilesAndPushToRemote(
      this.gitStatusResult,
      this.remoteBranchName,
      this.commitMessage,
      force
    );

    this.setGitPushResult(result);
    this.setPushingToRepo(false);

    if (result !== GitPushResult.Success) {
      await gitActionHandler.resetBranchAndFastForward(this.remoteBranchName);
      await this.diffCompiledProject();
      return;
    }

    // git push succeeded
    const params: OpenProjectMutation = {
      project: this.context.rootState.project.openedProject,
      config: this.context.rootState.project.openedProjectConfig,
      markAsDirty: false
    };
    await this.context.dispatch(`project/${ProjectViewActions.updateProject}`, params, { root: true });

    this.clearGitPushResult();
    this.clearGitStatusResult();

    // we have just pushed successfully, the current branch will have no changes
    this.setGitStatusResult([]);

    const repoBranches = await gitClient.listBranches();
    this.setRepoBranches(repoBranches);
    this.setCreatingNewBranch(false);
  }

  @LoggingAction
  public async forcePushToRemoteBranch() {
    await this.pushToRepo(true);
  }

  @LoggingAction
  public async pushToRemoteBranch() {
    await this.pushToRepo(false);
  }

  @LoggingAction
  public async runGitCommand(command: string): Promise<string> {
    if (this.projectSessionId === null) {
      const msg = 'Cannot run command with missing project session id';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }
    const gitClient = GitStoreModule.getGitClientByProjectId(this.projectSessionId);

    const gitCommandLookup: Record<string, () => Promise<string>> = {
      branches: async () => {
        return (await gitClient.listBranches()).join('\n');
      },
      status: async () => {
        return (await gitClient.status()).map(row => `${row[0]}: ${getStatusMessageForFileInfo(row)}`).join('\n');
      },
      log: async () => {
        return (await gitClient.log())
          .map(obj => {
            const commit = obj.commit;
            return {
              message: commit.message,
              parent: commit.parent,
              tree: commit.tree
            };
          })
          .map(obj => JSON.stringify(obj, null, 2))
          .join('\n');
      }
    };
    return gitCommandLookup[command] ? await gitCommandLookup[command]() : 'command not found';
  }

  @LoggingAction
  public async diffCompiledProject() {
    if (this.projectSessionId === null) {
      const msg = 'Cannot diff repo with missing project session id';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }

    // Force a save of the currently selected resource
    await this.context.dispatch(`project/${ProjectViewActions.saveSelectedResource}`, true, { root: true });

    const gitClient = GitStoreModule.getGitClientByProjectId(this.projectSessionId);
    const gitActionHandler = GitStoreModule.getRefineryGitActionHandler(this.projectSessionId);

    const project = await this.getOpenedProject();

    // TODO: See if we can move this logic into the Action handler to avoid breaking the Git abstraction
    if (this.creatingNewBranch) {
      await gitClient.branch({
        ref: this.remoteBranchName,
        checkout: true
      });
    } else {
      await gitClient.checkout({
        ref: this.remoteBranchName,
        force: true
      });
    }

    await gitActionHandler.writeProjectToDisk(project);

    // get list of files that were changed
    const statusResult = await gitClient.status();
    this.setGitStatusResult(statusResult);

    // get contents from changed files before and after they were modified
    // TODO this call will force checkout and compile the project again, there might be a way to optimize this
    const diffInfo = await gitActionHandler.getDiffFileInfo(
      project,
      this.remoteBranchName,
      this.gitStatusResult,
      this.creatingNewBranch
    );
    this.setGitDiffInfo(diffInfo);
  }

  @LoggingAction
  public async compileClonedProject(gitClient: GitClient): Promise<RefineryProject | null> {
    if (this.viewingProjectId === null) {
      const msg = 'Cannot compile clone repo with missing viewing project id';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }

    if (this.projectSessionId === null) {
      const msg = 'Cannot compile clone repo with missing project session id';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }

    try {
      return await loadProjectFromDir(gitClient.fs, this.viewingProjectId, this.projectSessionId, gitClient.dir);
    } catch (e) {
      if (e instanceof RepoCompilationError) {
        // this.setRepoCompilationError(e);
      }
      return this.context.rootState.project.openedProject;
    }
  }

  @LoggingAction
  public async setupLocalProjectRepo([projectConfig, projectId]: [ProjectConfig, string]) {
    if (!projectConfig.project_repo) {
      const msg = 'Unable to setup local project repo with missing git repo URI';
      console.error(msg);
      throw new InvalidGitRepoError(msg);
    }

    const projectSessionId = uuid.v4();

    this.setRandomSessionProjectId(projectSessionId);
    this.setViewingProjectId(projectId);

    GitStoreModule.createGitStore({
      projectId: projectSessionId,
      repoUri: projectConfig.project_repo
    });

    const gitClient = GitStoreModule.getGitClientByProjectId(projectSessionId);

    await gitClient.clone();

    const currentBranch = await gitClient.currentBranch();
    if (currentBranch) {
      this.setRemoteBranchName(currentBranch);
    }

    const repoBranches = await gitClient.listBranches({ remote: 'origin' });
    this.setRepoBranches(repoBranches);

    if (repoBranches.length === 0) {
      // there are no branches for us to push to, so we will have to make a new one
      this.setCreatingNewBranch(true);
    }

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
