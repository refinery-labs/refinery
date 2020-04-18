import { safeLoad } from 'js-yaml';
import LightningFS from '@isomorphic-git/lightning-fs';
import git, {
  AuthCallback,
  AuthFailureCallback,
  AuthSuccessCallback,
  CallbackFsClient,
  Errors,
  HttpClient,
  MessageCallback,
  ProgressCallback,
  PromiseFsClient,
  SignCallback,
  StatusRow
} from 'isomorphic-git';
import http from '@/repo-compiler/git-http';
import {
  isFileDeleted,
  isFileDeletedOrModified,
  isFileNew,
  listFilesInFolder,
  pathExists,
  readFile,
  statFile,
  tryReadFile
} from '@/repo-compiler/shared/git-utils';
import { REFINERY_PROJECTS_FOLDER } from '@/repo-compiler/shared/constants';
import { InvalidGitRepoStructure } from '@/repo-compiler/shared/errors';
import { RefineryProject } from '@/types/graph';
import { saveProjectToRepo } from '@/repo-compiler/one-to-one/refinery-to-git';
import { GitDiffInfo } from '@/repo-compiler/shared/git-types';
import { GitPushResult } from '@/store/modules/panes/sync-project-repo-pane';

export class GitClient {
  private readonly uri: string;
  public readonly fs: PromiseFsClient;
  public readonly dir: string;

  constructor(uri: string, projectID: string, resetFS?: boolean) {
    this.uri = uri;

    this.fs = new LightningFS('project', {
      wipe: resetFS === undefined ? false : resetFS
    });

    // TODO this needs to be unique per project in the case of a one to many repo
    this.dir = `/projects/${projectID}`;
  }

  public async checkout(
    options?: Partial<{
      fs: PromiseFsClient;
      onProgress?: ProgressCallback;
      dir: string;
      gitdir?: string;
      ref?: string;
      filepaths?: string[];
      remote?: string;
      noCheckout?: boolean;
      noUpdateHead?: boolean;
      dryRun?: boolean;
      force?: boolean;
    }>
  ) {
    await git.checkout({
      fs: this.fs,
      dir: this.dir,
      ...options
    });
  }

  public async clone(
    options?: Partial<{
      fs: PromiseFsClient;
      http: HttpClient;
      onProgress?: ProgressCallback;
      onMessage?: MessageCallback;
      onAuth?: AuthCallback;
      onAuthFailure?: AuthFailureCallback;
      onAuthSuccess?: AuthSuccessCallback;
      dir: string;
      gitdir?: string;
      url: string;
      corsProxy?: string;
      ref?: string;
      singleBranch?: boolean;
      noCheckout?: boolean;
      noTags?: boolean;
      remote?: string;
      depth?: number;
      since?: Date;
      exclude?: string[];
      relative?: boolean;
      headers?: {
        [x: string]: string;
      };
    }>
  ) {
    await git.clone({
      fs: this.fs,
      http,
      dir: this.dir,
      url: this.uri,
      corsProxy: `${process.env.VUE_APP_API_HOST}/api/v1/github/proxy`,
      ...options
    });
  }

  public async currentBranch(): Promise<string | undefined> {
    const currentBranch = await git.currentBranch({
      fs: this.fs,
      dir: this.dir
    });
    return currentBranch || undefined;
  }

  public async listBranches(
    options?: Partial<{
      remote?: string;
    }>
  ): Promise<string[]> {
    return await git.listBranches({
      fs: this.fs,
      dir: this.dir,
      ...options
    });
  }

  public async status(): Promise<Array<StatusRow>> {
    return await git.statusMatrix({
      fs: this.fs,
      dir: this.dir
    });
  }

  public async add(path: string) {
    await git.add({
      fs: this.fs,
      dir: this.dir,
      filepath: path
    });
  }

  public async remove(path: string) {
    await git.add({
      fs: this.fs,
      dir: this.dir,
      filepath: path
    });
  }

  public async commit(
    options?: Partial<{
      fs: CallbackFsClient | PromiseFsClient;
      onSign?: SignCallback;
      dir?: string;
      gitdir?: string;
      message: string;
      author?: {
        name?: string;
        email?: string;
        timestamp?: number;
        timezoneOffset?: number;
      };
      committer?: {
        name?: string;
        email?: string;
        timestamp?: number;
        timezoneOffset?: number;
      };
      signingKey?: string;
      dryRun?: boolean;
      noUpdateBranch?: boolean;
      ref?: string;
      parent?: string[];
      tree?: string;
    }>
  ) {
    await git.commit({
      fs: this.fs,
      dir: this.dir,
      message: '',
      ...options
    });
  }
  public async push(
    options?: Partial<{
      fs: CallbackFsClient | PromiseFsClient;
      http: HttpClient;
      onProgress?: ProgressCallback;
      onMessage?: MessageCallback;
      onAuth?: AuthCallback;
      onAuthFailure?: AuthFailureCallback;
      onAuthSuccess?: AuthSuccessCallback;
      dir?: string;
      gitdir?: string;
      ref?: string;
      url?: string;
      remote?: string;
      remoteRef?: string;
      force?: boolean;
      delete?: boolean;
      corsProxy?: string;
      headers?: {
        [x: string]: string;
      };
    }>
  ) {
    await git.push({
      fs: this.fs,
      dir: this.dir,
      http,
      ...options
    });
  }

  public async getProjectsList() {
    await this.clone({
      noCheckout: true
    });

    await this.checkout({
      filepaths: ['refinery/projects']
    });
  }

  /**
   * Grabs every Project file from a Git repo. Return format is list of paths to existing YAML files.
   * Should be called without any arguments, unless you have a specific use-case.
   * Will resolve directories recursively and return full paths for all located YAML files.
   * @param path Set to a the default value of the path for Refinery projects in the repo.
   */
  async readProjectsFromRepo(path = REFINERY_PROJECTS_FOLDER): Promise<string[]> {
    const projectsFolderExists = pathExists(this.fs, this.dir, path);

    if (!projectsFolderExists) {
      throw new InvalidGitRepoStructure('Missing projects folder');
    }

    // Grab every file in the Git repo at the given path
    const projectFiles = await listFilesInFolder(this.fs, this.dir, path);

    // Grab any nested directories
    const directories = await Promise.all(
      projectFiles.filter(async f => (await statFile(this.fs, this.dir, f)).isDirectory())
    );

    // Go grab all of the nested projects via recursive calls
    const nestedProjects: string[][] = await Promise.all(directories.map(this.readProjectsFromRepo));

    // Unpack the nested arrays
    const flattenedProjects = nestedProjects.flat(1);

    // List of files in the directory
    const files = projectFiles.filter(p => !directories.includes(p));

    // Grab only files that are of a type we care about (YAML)
    const yamlFiles = files.filter(p => p.endsWith('.yml') || p.endsWith('.yaml'));

    // Read the project from the YAML file
    const deserializedProjects = await Promise.all(
      yamlFiles.map(async yf => safeLoad(await readFile(this.fs, this.dir, path + yf)))
    );

    // Merge together all projects into a list
    return [...deserializedProjects, ...flattenedProjects];
  }

  public async saveProject(project: RefineryProject) {
    await saveProjectToRepo(this.fs, this.dir, project);
  }

  private async getFilesFromFS(filesToGet: string[]): Promise<Record<string, string>> {
    return filesToGet.reduce(async (fileLookup, file) => {
      const awaitedFileLookup = await fileLookup;
      const fileContent = (await tryReadFile(this.fs, this.dir, file)) || '';
      return {
        ...awaitedFileLookup,
        [file]: fileContent
      };
    }, Promise.resolve({} as Record<string, string>));
  }

  public async getDiffFileInfo(
    project: RefineryProject,
    branchName: string,
    gitStatusResult: Array<StatusRow>
  ): Promise<GitDiffInfo> {
    // TODO symlinks always show up as modified files
    const deletedModifiedFiles = gitStatusResult
      .filter(fileRow => isFileDeletedOrModified(fileRow))
      .map(fileRow => fileRow[0]);
    const newFiles = gitStatusResult.filter(fileRow => isFileNew(fileRow)).map(fileRow => fileRow[0]);

    await this.checkout({
      ref: branchName,
      force: true
    });

    // new files are ignored since they did not exist on the original branch
    const originalFileContents = await this.getFilesFromFS(deletedModifiedFiles);

    await this.saveProject(project);

    const changedFileContents = await this.getFilesFromFS([...deletedModifiedFiles, ...newFiles]);

    return {
      originalFiles: originalFileContents,
      changedFiles: changedFileContents
    };
  }

  public async stageFilesAndPushToRemote(
    gitStatusResult: Array<StatusRow>,
    branchName: string,
    commitMessage: string,
    force: boolean
  ) {
    const filesToDelete = gitStatusResult.filter(fileRow => isFileDeleted(fileRow)).map(fileRow => fileRow[0]);

    await this.add('.');
    await Promise.all(filesToDelete.map(async filepath => await this.remove(filepath)));

    await this.commit({
      author: {
        name: 'Refinery Bot',
        email: 'donotreply@refinery.io'
      },
      message: commitMessage
    });

    try {
      await this.push({
        remote: 'origin',
        remoteRef: branchName,
        corsProxy: `${process.env.VUE_APP_API_HOST}/api/v1/github/proxy`,
        force
      });
      return GitPushResult.Success;
    } catch (e) {
      if (e instanceof Errors.PushRejectedError) {
        return GitPushResult.UnableToFastForward;
      } else {
        return GitPushResult.Other;
      }
    }
  }
}
