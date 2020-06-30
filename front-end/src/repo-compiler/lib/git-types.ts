export interface LightningFsFile {
  type: 'file' | 'dir';
  mode: string;
  size: number;
  ino: number;
  mtimeMs: number;
  ctimeMs: number;
  // All below values are fixed to value of 1
  uid: number;
  gid: number;
  dev: number;

  isFile(): boolean;
  isDirectory(): boolean;
  isSymbolicLink(): boolean;
}

export interface GitStatusResult {
  newFiles: number;
  modifiedFiles: number;
  deletedFiles: number;
}

type GitDiffFilenameToContent = Record<string, string>;

export interface GitDiffInfo {
  originalFiles: GitDiffFilenameToContent;
  changedFiles: GitDiffFilenameToContent;
}

export class InvalidGitRepoError extends Error {}
