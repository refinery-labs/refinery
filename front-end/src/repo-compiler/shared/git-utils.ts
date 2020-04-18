import { CallbackFsClient, PromiseFsClient, StatusRow } from 'isomorphic-git';
import Path from 'path';
import { PROJECT_CONFIG_FILENAME } from '@/repo-compiler/shared/constants';
import { GitStatusResult, LightningFsFile } from '@/repo-compiler/shared/git-types';
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
  const result = await fs.promises
    .readlink(path)
    .catch((e: Error) => new RepoCompilationError(e.toString(), repoFileContext));
  if (result instanceof Error) {
    throw result;
  }
  return result;
}

export async function isPathValidSymlink(fs: PromiseFsClient, path: string) {
  const repoFileContext: RepoCompilationErrorContext = {
    filename: path
  };
  const pathLStat = await fs.promises
    .lstat(path)
    .catch((e: Error) => new RepoCompilationError(e.toString(), repoFileContext));
  if (pathLStat instanceof Error) {
    throw pathLStat;
  }
  const pathIsSymlink = pathLStat.isSymbolicLink();

  const pathStat = await fs.promises
    .lstat(path)
    .catch((e: Error) => new RepoCompilationError(e.toString(), repoFileContext));
  if (pathStat instanceof Error) {
    throw pathStat;
  }
  const resolvedPathExists = pathStat.isFile();

  return pathIsSymlink && resolvedPathExists;
}

/*
https://isomorphic-git.org/docs/en/statusMatrix
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
export function getStatusMessageForFileInfo(row: StatusRow): string {
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

export function getStatusForFileInfo(row: StatusRow): GitStatusResult {
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
      if (stageStatus === 1 || stageStatus === 2 || stageStatus === 3) {
        return { newFiles: 0, modifiedFiles: 1, deletedFiles: 0 };
      }
    }
  }
  return { newFiles: 0, modifiedFiles: 0, deletedFiles: 0 };
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

export function isFileDeletedOrModified(row: StatusRow): boolean {
  const headStatus = row[1];
  const workdirStatus = row[2];

  return headStatus === 1 && (workdirStatus === 0 || workdirStatus === 2);
}
