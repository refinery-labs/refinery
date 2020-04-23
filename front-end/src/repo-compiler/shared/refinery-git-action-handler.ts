import {
  REFINERY_COMMIT_AUTHOR_EMAIL,
  REFINERY_COMMIT_AUTHOR_NAME,
  REFINERY_PROJECTS_FOLDER
} from '@/repo-compiler/shared/constants';
import {
  isFileDeleted,
  isFileModified,
  isFileNew,
  listFilesInFolder,
  pathExists,
  readFile,
  statFile,
  tryReadFile
} from '@/repo-compiler/lib/git-utils';
import { InvalidGitRepoStructure } from '@/repo-compiler/shared/errors';
import { safeLoad } from 'js-yaml';
import { RefineryProject } from '@/types/graph';
import { saveProjectToRepo } from '@/repo-compiler/one-to-one/refinery-to-git';
import { Errors, StatusRow } from 'isomorphic-git';
import { GitDiffInfo } from '@/repo-compiler/lib/git-types';
import { GitPushResult } from '@/store/modules/panes/sync-project-repo-pane';
import { GitClient } from '@/repo-compiler/lib/git-client';

export class RefineryGitActionHandler {
  private gitClient: GitClient;

  constructor(gitClient: GitClient) {
    this.gitClient = gitClient;
  }

  public async getProjectsList() {
    await this.gitClient.clone({
      noCheckout: true
    });

    await this.gitClient.checkout({
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
    const projectsFolderExists = pathExists(this.gitClient.fs, this.gitClient.dir, path);

    if (!projectsFolderExists) {
      throw new InvalidGitRepoStructure('Missing projects folder');
    }

    // Grab every file in the Git repo at the given path
    const projectFiles = await listFilesInFolder(this.gitClient.fs, this.gitClient.dir, path);

    // Grab any nested directories
    const directories = await Promise.all(
      projectFiles.filter(async f => (await statFile(this.gitClient.fs, this.gitClient.dir, f)).isDirectory())
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
      yamlFiles.map(async yf => safeLoad(await readFile(this.gitClient.fs, this.gitClient.dir, path + yf)))
    );

    // Merge together all projects into a list
    return [...deserializedProjects, ...flattenedProjects];
  }

  public async writeProjectToDisk(project: RefineryProject) {
    await saveProjectToRepo(this.gitClient.fs, this.gitClient.dir, project);
  }

  private async getFilesFromFS(filesToGet: string[]): Promise<Record<string, string>> {
    const lookupArray = await Promise.all(
      filesToGet.map(async file => {
        const fileContent = (await tryReadFile(this.gitClient.fs, this.gitClient.dir, file)) || '';
        return {
          [file]: fileContent
        };
      })
    );
    return lookupArray.reduce(
      (lookup, lookupItem) => ({
        ...lookup,
        ...lookupItem
      }),
      {} as Record<string, string>
    );
  }

  public async getDiffFileInfo(
    project: RefineryProject,
    branchName: string,
    gitStatusResult: Array<StatusRow>
  ): Promise<GitDiffInfo> {
    // TODO symlinks always show up as modified files
    const deletedFiles = gitStatusResult.filter(fileRow => isFileDeleted(fileRow)).map(fileRow => fileRow[0]);
    const modifiedFiles = gitStatusResult.filter(fileRow => isFileModified(fileRow)).map(fileRow => fileRow[0]);

    const newFiles = gitStatusResult.filter(fileRow => isFileNew(fileRow)).map(fileRow => fileRow[0]);

    await this.gitClient.checkout({
      ref: branchName,
      force: true
    });

    // new files are ignored since they did not exist in HEAD
    const originalFileContents = await this.getFilesFromFS([...deletedFiles, ...modifiedFiles]);

    await this.writeProjectToDisk(project);

    // deleted files are ignored since they don't exist after the changes
    const changedFileContents = await this.getFilesFromFS([...modifiedFiles, ...newFiles]);

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
    const filesToAdd = gitStatusResult
      .filter(fileRow => isFileNew(fileRow) || isFileModified(fileRow))
      .map(fileRow => fileRow[0]);
    const filesToDelete = gitStatusResult.filter(fileRow => isFileDeleted(fileRow)).map(fileRow => fileRow[0]);

    console.log('git data: ', filesToAdd, filesToDelete);

    await Promise.all(filesToAdd.map(async filepath => await this.gitClient.add(filepath)));
    await Promise.all(filesToDelete.map(async filepath => await this.gitClient.remove(filepath)));

    await this.gitClient.commit({
      author: {
        name: REFINERY_COMMIT_AUTHOR_NAME,
        email: REFINERY_COMMIT_AUTHOR_EMAIL
      },
      message: commitMessage
    });

    try {
      await this.gitClient.push({
        remote: 'origin',
        remoteRef: branchName,
        corsProxy: `${process.env.VUE_APP_API_HOST}/api/v1/github/proxy`,
        force
      });
      return GitPushResult.Success;
    } catch (e) {
      if (e instanceof Errors.PushRejectedError) {
        console.log('Unable to FF');
        return GitPushResult.UnableToFastForward;
      } else {
        console.error(e);
        return GitPushResult.Other;
      }
    }
  }
}
