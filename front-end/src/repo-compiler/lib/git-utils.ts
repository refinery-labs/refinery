import { CallbackFsClient, PromiseFsClient, StatusRow } from 'isomorphic-git';
import Path from 'path';
import { PROJECT_CONFIG_FILENAME } from '@/repo-compiler/shared/constants';
import { GitStatusResult, LightningFsFile } from '@/repo-compiler/lib/git-types';
import { RefineryProject } from '@/types/graph';

export interface RepoCompilationErrorContext {
  filename?: string;
  fileContent?: string;
}

export class RepoCompilationError extends Error {
  errorContext: RepoCompilationErrorContext | undefined;

  constructor(message: string, errorContext?: RepoCompilationErrorContext) {
    super(message);

    this.name = 'RepoCompilationError';
    this.errorContext = errorContext;
  }
}

export async function pathExists(fs: PromiseFsClient, gitDir: string, path: string): Promise<boolean> {
  const filePath = Path.join(gitDir, path);

  try {
    await fs.promises.stat(filePath);

    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Reads a file and throws an exception if that file doesn't exist. Use {@link tryReadFile} or {@link pathExists} instead if you
 * aren't certain that a file exists.
 * @see {@link tryReadFile}
 * @see {@link pathExists}
 * @param fs Git Filesystem instance
 * @param gitDir Git directory of the repo inside of the Git Filesystem
 * @param path Path inside of the Git directory to look for the file
 */
export async function readFile(fs: PromiseFsClient, gitDir: string, path?: string): Promise<string> {
  // Merge the path together (if given 2 arguments) or use the path as-is.
  const filePath = path !== undefined ? Path.join(gitDir, path) : gitDir;

  const fileContent = await fs.promises.readFile(filePath);

  // for symlinks the file content will be a string
  if (typeof fileContent === 'string') {
    return fileContent;
  }

  return new TextDecoder('utf-8').decode(fileContent);
}

export async function tryReadFile(fs: PromiseFsClient, gitDir: string, path: string): Promise<string | null> {
  const exists = await pathExists(fs, gitDir, PROJECT_CONFIG_FILENAME);

  if (!exists) {
    return null;
  }

  return await readFile(fs, gitDir, path);
}

export async function listFilesInFolder(fs: PromiseFsClient, gitDir: string, path: string): Promise<string[]> {
  return await fs.promises.readdir(Path.join(gitDir, path));
}

export async function statFile(fs: PromiseFsClient, gitDir: string, path: string): Promise<LightningFsFile> {
  return await fs.promises.stat(Path.join(gitDir, path));
}

export async function readlink(fs: PromiseFsClient, path: string): Promise<string> {
  if (!fs.promises.readlink) {
    throw new RepoCompilationError('filesystem readlink function is not defined');
  }
  const repoFileContext: RepoCompilationErrorContext = {
    filename: path
  };
  try {
    return await fs.promises.readlink(path);
  } catch (e) {
    throw new RepoCompilationError(e.toString(), repoFileContext);
  }
}

async function pathIsSymlink(fs: PromiseFsClient, path: string) {
  const pathLStat = await fs.promises.lstat(path);
  return pathLStat.isSymbolicLink();
}

async function resolvedPathExists(fs: PromiseFsClient, path: string) {
  const pathStat = await fs.promises.lstat(path);
  return pathStat.isFile();
}

export async function isPathValidSymlink(fs: PromiseFsClient, path: string) {
  const repoFileContext: RepoCompilationErrorContext = {
    filename: path
  };

  try {
    return (await pathIsSymlink(fs, path)) && (await resolvedPathExists(fs, path));
  } catch (e) {
    throw new RepoCompilationError(e.toString(), repoFileContext);
  }
}

//https://isomorphic-git.org/docs/en/statusMatrix

/*
  ["a.txt", 0, 2, 0], // new, untracked
  ["b.txt", 0, 2, 2], // added, staged
  ["c.txt", 0, 2, 3], // added, staged, with unstaged changes
  ["d.txt", 1, 1, 1], // unmodified
  ["e.txt", 1, 2, 1], // modified, unstaged
  ["f.txt", 1, 2, 2], // modified, staged
  ["g.txt", 1, 2, 3], // modified, staged, with unstaged changes
  ["h.txt", 1, 0, 1], // deleted, unstaged
  ["i.txt", 1, 0, 0], // deleted, staged
 */

const STATUS_MAPPING: Record<string, string> = {
  '020': 'new, untracked',
  '022': 'added, staged',
  '023': 'added, staged, with unstaged changes',
  '100': 'deleted, staged',
  '101': 'deleted, unstaged',
  '111': 'unmodified',
  '121': 'modified, unstaged',
  '122': 'modified, staged',
  '123': 'modified, staged, with unstage changes'
};

export function getStatusMessageForFileInfo(row: StatusRow): string {
  const lookupKey = `${row[1]}${row[2]}${row[3]}`;

  return (lookupKey !== '' && STATUS_MAPPING[lookupKey]) || 'unknown git status';
}

const newFilesResult = () => ({ newFiles: 1, modifiedFiles: 0, deletedFiles: 0 });
const modifiedFilesResult = () => ({ newFiles: 0, modifiedFiles: 1, deletedFiles: 0 });
const deleteFilesResult = () => ({ newFiles: 0, modifiedFiles: 0, deletedFiles: 1 });

const GIT_RESULT_LOOKUP: Record<string, () => GitStatusResult> = {
  '020': newFilesResult,
  '022': newFilesResult,
  '023': newFilesResult,
  '100': deleteFilesResult,
  '101': deleteFilesResult,
  '121': modifiedFilesResult,
  '122': modifiedFilesResult,
  '123': modifiedFilesResult
};

export function getStatusForFileInfo(row: StatusRow): GitStatusResult {
  const lookupKey = `${row[1]}${row[2]}${row[3]}`;

  const lookupFn = lookupKey !== '' && GIT_RESULT_LOOKUP[lookupKey];

  if (!lookupFn) {
    // default case
    return { newFiles: 0, modifiedFiles: 0, deletedFiles: 0 };
  }

  return lookupFn();
}

export function isFileUnmodified(row: StatusRow): boolean {
  const headStatus = row[1];
  const workdirStatus = row[2];
  const stageStatus = row[3];

  return headStatus === 1 && workdirStatus === 1 && stageStatus === 1;
}

export function isFileNew(row: StatusRow): boolean {
  const headStatus = row[1];
  const workdirStatus = row[2];

  return headStatus === 0 && workdirStatus === 2;
}

export function isFileDeleted(row: StatusRow): boolean {
  const headStatus = row[1];
  const workdirStatus = row[2];

  return headStatus === 1 && workdirStatus === 0;
}

export function isFileModified(row: StatusRow): boolean {
  const headStatus = row[1];
  const workdirStatus = row[2];

  return headStatus === 1 && workdirStatus === 2;
}
