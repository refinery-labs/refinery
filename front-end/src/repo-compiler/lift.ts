import {
  LambdaWorkflowState,
  RefineryProject,
  WorkflowFile,
  WorkflowFileLink,
  WorkflowFileLinkType,
  WorkflowFileType
} from '@/types/graph';
import LightningFS from '@isomorphic-git/lightning-fs';
import git, { PromiseFsClient } from 'isomorphic-git';
import http from '@/repo-compiler/git-http';

import Path from 'path';
import yaml from 'js-yaml';
import uuid from 'uuid/v4';
import { languageToFileExtension } from '@/utils/project-debug-utils';
import generateStupidName from '@/lib/silly-names';

class RepoCompilationError extends Error {}

function repoError(e: Error): RepoCompilationError {
  return new RepoCompilationError(e.toString());
}

const PROJECT_CONFIG_FILENAME = 'project.yaml';
const PROJECT_LAMBDA_DIR = 'lambda';
const PROJECT_SHARED_FILES_DIR = 'shared-files';

const LAMBDA_CONFIG_FILENAME = 'config.yaml';
const LAMBDA_SHARED_FILES_DIR = 'shared_files';

const BLOCK_CODE_FILENAME = 'block_code';

type WorkflowFileLookup = Record<string, WorkflowFile>;

async function pathExists(fs: PromiseFsClient, dir: string, file: string) {
  const filePath = Path.join(dir, file);
  if (!(await fs.promises.stat(filePath).catch(() => false))) {
    throw new RepoCompilationError(`unable to find ${file} in ${dir}`);
  }
  return filePath;
}

async function readFile(fs: PromiseFsClient, path: string): Promise<string> {
  const fileContent = await fs.promises.readFile(path);
  return new TextDecoder('utf-8').decode(fileContent);
}

async function loadLambdaCode(
  fs: PromiseFsClient,
  lambdaPath: string,
  blockConfig: LambdaWorkflowState
): Promise<string> {
  if (!blockConfig.language) {
    throw new RepoCompilationError(`no language set in block ${lambdaPath}`);
  }
  const extension = languageToFileExtension[blockConfig.language];
  const blockCodeFilename = `${BLOCK_CODE_FILENAME}.${extension}`;
  const blockCodePath = Path.join(lambdaPath, blockCodeFilename);

  return await readFile(fs, blockCodePath);
}

async function loadLambdaBlock(fs: PromiseFsClient, lambdaPath: string): Promise<LambdaWorkflowState> {
  const blockConfigPath = await pathExists(fs, lambdaPath, LAMBDA_CONFIG_FILENAME);
  const blockConfig = yaml.safeLoad(await readFile(fs, blockConfigPath)) as LambdaWorkflowState;

  return {
    id: uuid(),
    ...blockConfig,
    code: await loadLambdaCode(fs, lambdaPath, blockConfig)
  };
}

async function readlink(fs: PromiseFsClient, path: string): Promise<string> {
  if (!fs.promises.readlink) {
    throw new RepoCompilationError('filesystem readlink function is not defined');
  }
  const result = await fs.promises.readlink(path).catch(repoError);
  if (result instanceof Error) {
    throw result;
  }
  return result;
}

function getLambdaSharedFileLink(
  lambdaNode: string,
  sharedFileTargetRelativePath: string,
  sharedFileLinkPath: string,
  sharedFileLookup: WorkflowFileLookup
): WorkflowFileLink {
  const lambdaSharedFilesPath = Path.dirname(sharedFileLinkPath);
  const sharedFilePath = Path.resolve(lambdaSharedFilesPath, sharedFileTargetRelativePath);

  const sharedFileConfig = sharedFileLookup[sharedFilePath];
  if (!sharedFileConfig) {
    throw new RepoCompilationError(`lambda shared file was not found in shared file folder ${sharedFilePath}`);
  }

  return {
    id: uuid(),
    node: lambdaNode,
    version: '1.0.0',
    file_id: sharedFileConfig.id,
    path: '',
    type: WorkflowFileLinkType.SHARED_FILE_LINK
  };
}

async function isPathValidSymlink(fs: PromiseFsClient, path: string) {
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

async function loadLambdaSharedBlocks(
  fs: PromiseFsClient,
  lambdaPath: string,
  lambdaNode: string,
  sharedFileLookup: WorkflowFileLookup
): Promise<WorkflowFileLink[]> {
  const sharedFileLinksPath = Path.join(lambdaPath, LAMBDA_SHARED_FILES_DIR);
  if (!(await fs.promises.stat(sharedFileLinksPath).catch(() => false))) {
    return [];
  }

  const sharedFileLinks = await fs.promises.readdir(sharedFileLinksPath);
  return Promise.all(
    sharedFileLinks
      .map((sharedFileLink: string) => Path.join(sharedFileLinksPath, sharedFileLink))
      .filter(async (sharedFileLinkPath: string) => await isPathValidSymlink(fs, sharedFileLinkPath))
      .map(async (sharedFileLinkPath: string) => {
        const sharedFileTargetRelativePath = await readlink(fs, sharedFileLinkPath);
        return getLambdaSharedFileLink(lambdaNode, sharedFileTargetRelativePath, sharedFileLinkPath, sharedFileLookup);
      })
  );
}

interface LoadedLambdaConfigs {
  sharedFileLinks: WorkflowFileLink[];
  lambdaBlockConfigs: LambdaWorkflowState[];
}

async function loadLambdaBlocks(
  fs: PromiseFsClient,
  repoDir: string,
  sharedFileLookup: WorkflowFileLookup
): Promise<LoadedLambdaConfigs> {
  const lambdaPath = Path.join(repoDir, PROJECT_LAMBDA_DIR);
  if (!(await fs.promises.stat(lambdaPath).catch(() => false))) {
    return {
      sharedFileLinks: [],
      lambdaBlockConfigs: []
    };
  }

  const lambdas = await fs.promises.readdir(lambdaPath);
  return await lambdas
    .map((lambdaFilename: string) => Path.join(lambdaPath, lambdaFilename))
    .reduce(async (loadedConfigs: Promise<LoadedLambdaConfigs>, lambdaPath: string) => {
      const resolvedLoadedConfigs = await loadedConfigs;

      const lambdaBlock = await loadLambdaBlock(fs, lambdaPath);
      const sharedFileLinks = await loadLambdaSharedBlocks(fs, lambdaPath, lambdaBlock.id, sharedFileLookup);

      return {
        sharedFileLinks: [...resolvedLoadedConfigs.sharedFileLinks, ...sharedFileLinks],
        lambdaBlockConfigs: [...resolvedLoadedConfigs.lambdaBlockConfigs, lambdaBlock]
      };
    }, Promise.resolve({ sharedFileLinks: [], lambdaBlockConfigs: [] } as LoadedLambdaConfigs));
}

async function loadSharedFileConfig(
  fs: PromiseFsClient,
  sharedFilePath: string,
  sharedFileName: string
): Promise<WorkflowFile> {
  return {
    id: uuid(),
    name: sharedFileName,
    version: '1.0.0',
    body: await readFile(fs, sharedFilePath),
    type: WorkflowFileType.SHARED_FILE
  };
}

async function loadSharedFiles(fs: PromiseFsClient, repoDir: string): Promise<WorkflowFileLookup> {
  const sharedFilesPath = Path.join(repoDir, PROJECT_SHARED_FILES_DIR);
  if (!(await fs.promises.stat(sharedFilesPath).catch(() => false))) {
    return {};
  }

  const sharedFiles = await fs.promises.readdir(sharedFilesPath);
  return await sharedFiles.reduce(async (lookup: Promise<WorkflowFileLookup>, sharedFileName: string) => {
    const resolvedLookup = await lookup;
    const sharedFilePath = Path.join(sharedFilesPath, sharedFileName);
    return {
      ...resolvedLookup,
      [sharedFilePath]: await loadSharedFileConfig(fs, sharedFilePath, sharedFileName)
    };
  }, Promise.resolve({} as WorkflowFileLookup));
}

async function loadProjectFromDir(fs: PromiseFsClient, projectID: string, repoDir: string): Promise<RefineryProject> {
  const projectConfigFilename = await pathExists(fs, repoDir, PROJECT_CONFIG_FILENAME);
  const loadedProjectConfig = yaml.safeLoad(await readFile(fs, projectConfigFilename)) as RefineryProject;

  const sharedFileLookup = await loadSharedFiles(fs, repoDir);
  const sharedFileConfigs = Object.values(sharedFileLookup);

  const loadedLambdaConfigs = await loadLambdaBlocks(fs, repoDir, sharedFileLookup);

  return {
    // default values
    name: generateStupidName(),
    version: 1,
    project_id: projectID,
    workflow_relationships: [],
    readme: '',

    // overridden values by project config
    ...loadedProjectConfig,

    // values tracked by file system
    workflow_states: [...loadedProjectConfig.workflow_states, ...loadedLambdaConfigs.lambdaBlockConfigs],
    workflow_files: [...loadedProjectConfig.workflow_files, ...sharedFileConfigs],
    workflow_file_links: [...loadedProjectConfig.workflow_file_links, ...loadedLambdaConfigs.sharedFileLinks]
  };
}

export async function compileProjectRepo(projectID: string, gitURL: string): Promise<RefineryProject | null> {
  const fs = new LightningFS('project', { wipe: true });
  const dir = '/project';

  await git.clone({
    fs,
    http,
    dir,
    url: gitURL,
    corsProxy: `${process.env.VUE_APP_API_HOST}/api/v1/github/proxy`
  });

  // TODO cleanup fs?
  return await loadProjectFromDir(fs, projectID, dir).catch(e => {
    console.error(e);
    return null;
  });
}
