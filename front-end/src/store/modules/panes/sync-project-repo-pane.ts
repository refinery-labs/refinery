import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { compileProjectRepo } from '@/repo-compiler/lift';
import { ProjectViewActions, ProjectViewMutators } from '@/constants/store-constants';
import { OpenProjectMutation } from '@/types/project-editor-types';
import { commitAndPushToRepo, saveProjectToRepo } from '@/repo-compiler/drop';
import { ProjectConfig, RefineryProject } from '@/types/graph';
import LightningFS from '@isomorphic-git/lightning-fs';
import git, { Errors, PromiseFsClient, StatusRow } from 'isomorphic-git';
import http from '@/repo-compiler/git-http';

const storeName = StoreType.syncProjectRepo;

export enum GitPushResult {
  Success = 'Success',
  UnableToFastForward = 'UnableToFastForward',
  Other = 'Other'
}

const gitPushResultToMessage: Record<GitPushResult, string> = {
  [GitPushResult.Success]: 'Successfully pushed to remote branch',
  [GitPushResult.UnableToFastForward]:
    'Unable to fast forward, you can force push your project to your remote branch, overwriting any remote changes.',
  [GitPushResult.Other]: 'Some unknown git push error has occurred'
};

// Types
export interface SyncProjectRepoPaneState {
  remoteBranchName: string;
  gitStatusResult: Array<StatusRow>;
  gitPushResult: GitPushResult | undefined;
  repoBranches: string[];
}

// Initial State
const moduleState: SyncProjectRepoPaneState = {
  remoteBranchName: 'master',
  gitStatusResult: [],
  gitPushResult: undefined,
  repoBranches: []
};

const initialState = deepJSONCopy(moduleState);

export interface GitStatusResult {
  newFiles: number;
  modifiedFiles: number;
  deletedFiles: number;
}

/*
example StatusMatrix
[
  ["a.txt", 0, 2, 0], // new, untracked
  ["b.txt", 0, 2, 2], // added, staged
  ["c.txt", 0, 2, 3], // added, staged, with unstaged changes
  ["d.txt", 1, 1, 1], // unmodified
  ["e.txt", 1, 2, 1], // modified, unstaged
  ["f.txt", 1, 2, 2], // modified, staged
  ["g.txt", 1, 2, 3], // modified, staged, with unstaged changes
  ["h.txt", 1, 0, 1], // deleted, unstaged
  ["i.txt", 1, 0, 0], // deleted, staged
]
 */
function getStatusMessageForFileInfo(row: StatusRow): string {
  const headStatus = row[1];
  const workdirStatus = row[2];
  const stageStatus = row[3];

  if (headStatus === 0) {
    if (workdirStatus === 2) {
      if (stageStatus === 0) return 'new, untracked';
      if (stageStatus === 2) return 'added, staged';
      if (stageStatus === 3) return 'added, staged, with unstaged changes';
    }
  } else {
    // headStatus === 1
    if (workdirStatus === 0) {
      if (stageStatus === 0) return 'deleted, staged';
      if (stageStatus === 1) return 'deleted, unstaged';
    }
    if (workdirStatus === 1) {
      if (stageStatus === 1) return 'unmodified';
    }
    if (workdirStatus === 2) {
      if (stageStatus === 1) return 'modified, unstaged';
      if (stageStatus === 2) return 'modified, staged';
      if (stageStatus === 3) return 'modified, staged, with unstage changes';
    }
  }
  return 'unknown git status';
}

function getStatusForFileInfo(row: StatusRow): GitStatusResult {
  const headStatus = row[1];
  const workdirStatus = row[2];
  const stageStatus = row[3];

  if (headStatus === 0) {
    if (workdirStatus === 2) {
      if (stageStatus === 0 || stageStatus === 2 || stageStatus === 3) {
        return { newFiles: 1, modifiedFiles: 0, deletedFiles: 0 };
      }
    }
  } else {
    // headStatus === 1
    if (workdirStatus === 0) {
      if (stageStatus === 0 || stageStatus === 1) {
        return { newFiles: 0, modifiedFiles: 0, deletedFiles: 1 };
      }
    }
    if (workdirStatus === 2) {
      if (stageStatus === 2 || stageStatus === 3) {
        return { newFiles: 0, modifiedFiles: 1, deletedFiles: 0 };
      }
    }
  }
  return { newFiles: 0, modifiedFiles: 0, deletedFiles: 0 };
}

function getProjectRepoDir(project: RefineryProject): string {
  return `/${project.project_id}`;
}

@Module({ namespaced: true, name: storeName })
export class SyncProjectRepoPaneStore extends VuexModule<ThisType<SyncProjectRepoPaneState>, RootState>
  implements SyncProjectRepoPaneState {
  public remoteBranchName: string = initialState.remoteBranchName;
  public gitStatusResult: Array<StatusRow> = initialState.gitStatusResult;
  public gitPushResult: GitPushResult | undefined = initialState.gitPushResult;
  public repoBranches: string[] = initialState.repoBranches;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  get isGitPushResultSet(): boolean {
    return this.gitPushResult !== undefined;
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

  get formattedGitStatusResult(): string {
    return this.gitStatusResult.map(fileRow => `${fileRow[0]}: ${getStatusMessageForFileInfo(fileRow)}`).join('\n');
  }

  get getRepoBranches(): string[] {
    return this.repoBranches;
  }

  @Mutation
  public async setRemoteBranchName(remoteBranchName: string) {
    this.remoteBranchName = remoteBranchName;
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

  @Action
  public getOpenedProject(): RefineryProject | undefined {
    if (!this.context.rootState.project.openedProject) {
      console.error('no project open or no project config');
      return undefined;
    }
    return this.context.rootState.project.openedProject;
  }

  @Action
  public getOpenedProjectConfig(): ProjectConfig | undefined {
    if (!this.context.rootState.project.openedProjectConfig) {
      console.error('no project open or no project config');
      return undefined;
    }
    return this.context.rootState.project.openedProjectConfig;
  }

  @Action
  public async setupProjectGitRepo(projectRepoURL: string): Promise<PromiseFsClient | undefined> {
    const project = await this.getOpenedProject();
    if (!project) {
      console.error('project or project config not set');
      return;
    }

    const fs = new LightningFS('project', { wipe: true }) as PromiseFsClient;

    await git.clone({
      fs,
      http,
      dir: getProjectRepoDir(project),
      url: projectRepoURL,
      corsProxy: `${process.env.VUE_APP_API_HOST}/api/v1/github/proxy`
    });

    // TODO make sure clone was successful

    this.setRepoBranches(
      await git.listBranches({
        fs,
        dir: getProjectRepoDir(project)
      })
    );

    return fs;
  }

  @Action
  public async pushToRepo(force: boolean) {
    const project = await this.getOpenedProject();
    if (!project) {
      console.error('project not set');
      return;
    }

    const fs = new LightningFS('project') as PromiseFsClient;

    if (!(await fs.promises.stat(getProjectRepoDir(project)).catch(() => false))) {
      console.error('no project was found in local filesystem');
      return;
    }

    const result = await commitAndPushToRepo(fs, getProjectRepoDir(project), this.remoteBranchName, force)
      .then(() => GitPushResult.Success)
      .catch((e: Error) => {
        if (e instanceof Errors.PushRejectedError) {
          return GitPushResult.UnableToFastForward;
        } else {
          return GitPushResult.Other;
        }
      });
    this.setGitPushResult(result);
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
  public async diffCompiledProject() {
    this.setGitPushResult(undefined);

    const project = await this.getOpenedProject();
    const projectConfig = await this.getOpenedProjectConfig();
    if (!project || !projectConfig || !projectConfig.project_repo) {
      console.error('project or project config not set');
      return;
    }

    const fs = new LightningFS('project') as PromiseFsClient;

    // TODO fs folder should be project id
    const statusMatrix = await saveProjectToRepo(fs, getProjectRepoDir(project), project);
    this.setGitStatusResult(statusMatrix);
  }

  @Action
  public async setupLocalProjectRepo(projectConfig: ProjectConfig) {
    const project = await this.getOpenedProject();
    if (!project || !projectConfig || !projectConfig.project_repo) {
      console.error('project or project config not set');
      return;
    }

    const fs = await this.setupProjectGitRepo(projectConfig.project_repo);
    if (!fs) {
      console.error('unable to create local filesystem');
      return;
    }

    // TODO fs folder should be project id
    const compiledProject = await compileProjectRepo(fs, getProjectRepoDir(project));

    const config = this.context.rootState.project.openedProjectConfig;

    this.context.commit(ProjectViewMutators.resetState);

    const params: OpenProjectMutation = {
      project: compiledProject,
      config: config,
      markAsDirty: false
    };

    await this.context.dispatch(`project/${ProjectViewActions.updateProject}`, params, { root: true });
  }
}
