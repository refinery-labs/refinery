import { CallbackFsClient, PromiseFsClient } from 'isomorphic-git';
import Path from 'path';
import { PROJECT_CONFIG_FILENAME } from '@/repo-compiler/shared/constants';
import { LightningFsFile } from '@/repo-compiler/shared/git-types';

export class RepoCompilationError extends Error {}

export function repoError(e: Error): RepoCompilationError {
  return new RepoCompilationError(e.toString());
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
  const result = await fs.promises.readlink(path).catch(repoError);
  if (result instanceof Error) {
    throw result;
  }
  return result;
}

export async function isPathValidSymlink(fs: PromiseFsClient, path: string) {
  const pathLStat = await fs.promises.lstat(path).catch((e: Error) => new RepoCompilationError(e.toString()));
  if (pathLStat instanceof Error) {
    throw pathLStat;
  }
  const pathIsSymlink = pathLStat.isSymbolicLink();

  const pathStat = await fs.promises.lstat(path).catch(repoError);
  if (pathStat instanceof Error) {
    throw pathStat;
  }
  const resolvedPathExists = pathStat.isFile();

  return pathIsSymlink && resolvedPathExists;
}
