import { safeLoad } from 'js-yaml';
import LightningFS from '@isomorphic-git/lightning-fs';
import git, {
  AuthCallback,
  AuthFailureCallback,
  AuthSuccessCallback,
  HttpClient,
  MessageCallback,
  ProgressCallback,
  PromiseFsClient
} from 'isomorphic-git';
import http from '@/repo-compiler/git-http';
import { listFilesInFolder, pathExists, readFile, statFile, tryReadFile } from '@/repo-compiler/shared/git-utils';
import { REFINERY_PROJECTS_FOLDER } from '@/repo-compiler/shared/constants';
import { InvalidGitRepoStructure } from '@/repo-compiler/shared/errors';

export class GitClient {
  private readonly uri: string;
  public readonly fs: PromiseFsClient;
  public readonly dir: string;

  constructor(uri: string) {
    this.uri = uri;

    this.fs = new LightningFS('project', {
      // TODO: Sort out of this is actually necessary or not
      // wipe: true
    });

    this.dir = `/projects/${encodeURIComponent(uri)}`;
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
}
