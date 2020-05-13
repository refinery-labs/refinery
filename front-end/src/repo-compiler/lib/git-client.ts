import git, {
  AuthCallback,
  AuthFailureCallback,
  AuthSuccessCallback,
  CallbackFsClient,
  CommitObject,
  HttpClient,
  MessageCallback,
  ProgressCallback,
  PromiseFsClient,
  ReadCommitResult,
  SignCallback,
  StatusRow
} from 'isomorphic-git';
import { http } from '@/repo-compiler/lib/git-http';

export class GitClient {
  private readonly uri: string;
  public readonly fs: PromiseFsClient;
  public readonly dir: string;

  constructor(uri: string, fs: PromiseFsClient, dir: string, resetFS?: boolean) {
    this.uri = uri;

    this.fs = fs;

    // TODO this needs to be unique per project in the case of a one to many repo
    this.dir = dir;
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

  public async branch(
    options?: Partial<{
      fs: CallbackFsClient | PromiseFsClient;
      dir?: string;
      gitdir?: string;
      ref: string;
      checkout?: boolean;
    }>
  ) {
    await git.branch({
      fs: this.fs,
      dir: this.dir,
      ref: 'master',
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

    if (currentBranch === '') {
      return '';
    }
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

  public async deleteBranch(ref: string): Promise<void> {
    return await git.deleteBranch({
      fs: this.fs,
      dir: this.dir,
      ref: ref
    });
  }

  public async log(): Promise<Array<ReadCommitResult>> {
    return await git.log({
      fs: this.fs,
      dir: this.dir
    });
  }

  public async fastForward(
    options?: Partial<{
      fs: CallbackFsClient | PromiseFsClient;
      http: HttpClient;
      onProgress?: ProgressCallback;
      onMessage?: MessageCallback;
      onAuth?: AuthCallback;
      onAuthFailure?: AuthFailureCallback;
      onAuthSuccess?: AuthSuccessCallback;
      dir: string;
      gitdir?: string;
      ref?: string;
      url?: string;
      remote?: string;
      remoteRef?: string;
      corsProxy?: string;
      singleBranch?: boolean;
      headers?: {
        [x: string]: string;
      };
    }>
  ): Promise<void> {
    return await git.fastForward({
      fs: this.fs,
      dir: this.dir,
      http,
      ref: 'master',
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
    await git.remove({
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
}