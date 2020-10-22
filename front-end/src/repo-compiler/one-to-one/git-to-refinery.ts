import {
  LambdaWorkflowState,
  RefineryProject,
  WorkflowFile,
  WorkflowFileLink,
  WorkflowFileLinkType,
  WorkflowFileType
} from '@/types/graph';
import { PromiseFsClient } from 'isomorphic-git';
import Path from 'path';
import yaml from 'js-yaml';
import uuid from 'uuid/v4';
import { languageToFileExtension } from '@/utils/project-debug-utils';
import generateStupidName from '@/lib/silly-names';
import { LoadedLambdaConfigs, WorkflowFileLookup } from '@/repo-compiler/one-to-one/types';
import {
  BLOCK_CODE_FILENAME,
  GLOBAL_BASE_PATH,
  LAMBDA_CONFIG_FILENAME,
  LAMBDA_SHARED_FILES_DIR,
  PROJECT_LAMBDA_DIR,
  PROJECT_SHARED_FILES_DIR,
  PROJECTS_CONFIG_FOLDER,
  README_FILENAME
} from '@/repo-compiler/shared/constants';
import {
  isPathValidSymlink,
  listFilesInFolder,
  pathExists,
  readFile,
  readlink,
  RepoCompilationError,
  RepoCompilationErrorContext
} from '@/repo-compiler/lib/git-utils';

async function loadLambdaCode(
  fs: PromiseFsClient,
  lambdaPath: string,
  blockConfig: LambdaWorkflowState
): Promise<string> {
  if (!blockConfig.language) {
    const repoContext: RepoCompilationErrorContext = {
      filename: lambdaPath,
      fileContent: JSON.stringify(blockConfig)
    };
    throw new RepoCompilationError(`no language set in block`, repoContext);
  }
  const extension = languageToFileExtension[blockConfig.language];
  const blockCodeFilename = `${BLOCK_CODE_FILENAME}.${extension}`;
  const blockCodePath = Path.join(lambdaPath, blockCodeFilename);

  return await readFile(fs, blockCodePath);
}

async function loadLambdaBlock(fs: PromiseFsClient, lambdaPath: string): Promise<LambdaWorkflowState> {
  const blockConfigPathExists = await pathExists(fs, lambdaPath, LAMBDA_CONFIG_FILENAME);

  if (!blockConfigPathExists) {
    const repoContext: RepoCompilationErrorContext = {
      filename: Path.join(lambdaPath, LAMBDA_CONFIG_FILENAME)
    };
    throw new RepoCompilationError('Lambda block does not exist', repoContext);
  }

  // TODO: Replace with a validator for the JSON contents
  const blockConfig = yaml.safeLoad(await readFile(fs, lambdaPath, LAMBDA_CONFIG_FILENAME)) as LambdaWorkflowState;

  return {
    id: uuid(),
    ...blockConfig,
    code: await loadLambdaCode(fs, lambdaPath, blockConfig)
  };
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
    const repoContext: RepoCompilationErrorContext = {
      filename: sharedFilePath
    };
    throw new RepoCompilationError(`lambda shared file was not found in shared file folder`, repoContext);
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

async function loadLambdaSharedBlocks(
  fs: PromiseFsClient,
  lambdaPath: string,
  lambdaNode: string,
  sharedFileLookup: WorkflowFileLookup
): Promise<WorkflowFileLink[]> {
  const sharedFileLinksPath = Path.join(lambdaPath, LAMBDA_SHARED_FILES_DIR);

  try {
    await fs.promises.stat(sharedFileLinksPath);
  } catch (e) {
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

async function loadLambdaBlocks(
  fs: PromiseFsClient,
  repoDir: string,
  sharedFileLookup: WorkflowFileLookup
): Promise<LoadedLambdaConfigs> {
  const lambdaPath = Path.join(repoDir, GLOBAL_BASE_PATH, PROJECT_LAMBDA_DIR);
  try {
    await fs.promises.stat(lambdaPath);
  } catch (e) {
    console.error('Could not stat block: ' + lambdaPath);
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
  const sharedFilesPath = Path.join(repoDir, GLOBAL_BASE_PATH, PROJECT_SHARED_FILES_DIR);

  try {
    await fs.promises.stat(sharedFilesPath);
  } catch (e) {
    console.error('Could not stat shared file folder: ' + sharedFilesPath);
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

export async function loadProjectFromDir(
  fs: PromiseFsClient,
  projectID: string,
  sessionID: string,
  repoDir: string
): Promise<RefineryProject> {
  const projectConfigFilename = Path.join(GLOBAL_BASE_PATH, `${PROJECTS_CONFIG_FOLDER}${projectID}.yaml`);
  const projectConfigExists = await pathExists(fs, repoDir, projectConfigFilename);

  if (!projectConfigExists) {
    const repoContext: RepoCompilationErrorContext = {
      filename: projectConfigFilename
    };
    throw new RepoCompilationError('Project config does not exist', repoContext);
  }

  // TODO: Add validation of object here
  const loadedProjectConfig = yaml.safeLoad(await readFile(fs, repoDir, projectConfigFilename)) as RefineryProject;

  const sharedFileLookup = await loadSharedFiles(fs, repoDir);
  const sharedFileConfigs = Object.values(sharedFileLookup);

  const loadedLambdaConfigs = await loadLambdaBlocks(fs, repoDir, sharedFileLookup);

  return {
    // default values
    name: generateStupidName(),
    version: 1,
    workflow_relationships: [],

    // overridden values by project config
    ...loadedProjectConfig,

    // Must happen after merging of the loaded Project config, otherwise can result in clobbering of UUIDs between projects
    project_id: projectID,

    // values tracked by file system
    workflow_states: [...loadedProjectConfig.workflow_states, ...loadedLambdaConfigs.lambdaBlockConfigs],
    workflow_files: [...loadedProjectConfig.workflow_files, ...sharedFileConfigs],
    workflow_file_links: [...loadedProjectConfig.workflow_file_links, ...loadedLambdaConfigs.sharedFileLinks]
  };
}
