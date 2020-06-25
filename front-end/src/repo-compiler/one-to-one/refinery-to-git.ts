import {
  LambdaWorkflowState,
  RefineryProject,
  WorkflowFile,
  WorkflowFileLink,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { convertProjectDownloadZipConfigToFileList, createDownloadZipConfig } from '@/utils/project-debug-utils';
import git, { WORKDIR, PromiseFsClient, WalkerEntry } from 'isomorphic-git';
import Path from 'path';
import slugify from 'slugify';
import yaml from 'js-yaml';
import {
  GLOBAL_BASE_PATH,
  LAMBDA_SHARED_FILES_DIR,
  PROJECT_SHARED_FILES_DIR,
  PROJECTS_CONFIG_FOLDER,
  README_FILENAME
} from '@/repo-compiler/shared/constants';

function getFolderName(name: string) {
  return slugify(name).toLowerCase();
}

async function writeConfig(fs: PromiseFsClient, out: string, data: any) {
  const serializedConfig = yaml.safeDump(data);
  await fs.promises.writeFile(out, serializedConfig);
}

async function getLambdaDir(fs: PromiseFsClient, lambdaDir: string, lambdaId: string): Promise<string> {
  try {
    await fs.promises.stat(lambdaDir);
    const firstPartOfId = lambdaId.split('-')[0];
    return `${lambdaDir}-${firstPartOfId}`;
  } catch (e) {
    return lambdaDir;
  }
}

async function handleLambda(
  fs: PromiseFsClient,
  projectDir: string,
  project: RefineryProject,
  workflowState: WorkflowState
): Promise<string> {
  const lambda = workflowState as LambdaWorkflowState;

  const typePath = Path.join(projectDir, GLOBAL_BASE_PATH, getFolderName(workflowState.type));
  await maybeMkdir(fs, typePath);

  const blockDir = getFolderName(lambda.name);

  // check if we have a name collision with an existing lambda
  // if so, we append the first part of the idea to the folder name
  const lambdaDir = await getLambdaDir(fs, Path.join(typePath, blockDir), lambda.id);
  await maybeMkdir(fs, lambdaDir);

  const config = createDownloadZipConfig(project, lambda);
  const filesToZip = convertProjectDownloadZipConfigToFileList(config);

  await Promise.all(
    filesToZip.map(async file => {
      const path = Path.join(lambdaDir, file.fileName);
      await fs.promises.writeFile(path, file.contents);
    })
  );

  // remove code from the config since we are tracking it via the file system
  const newLambda = {
    ...lambda,
    code: ''
  };

  const lambdaConfig = Path.join(lambdaDir, 'config.yaml');
  await writeConfig(fs, lambdaConfig, newLambda);

  return lambdaDir;
}

async function defaultHandler(
  fs: PromiseFsClient,
  projectDir: string,
  project: RefineryProject,
  workflowState: WorkflowState
): Promise<string> {
  return '';
}

const workflowStateActions: Record<
  WorkflowStateType,
  (fs: PromiseFsClient, projectDir: string, project: RefineryProject, e: WorkflowState) => Promise<string>
> = {
  [WorkflowStateType.LAMBDA]: handleLambda,
  [WorkflowStateType.API_ENDPOINT]: defaultHandler,
  [WorkflowStateType.API_GATEWAY]: defaultHandler,
  [WorkflowStateType.API_GATEWAY_RESPONSE]: defaultHandler,
  [WorkflowStateType.SCHEDULE_TRIGGER]: defaultHandler,
  [WorkflowStateType.SNS_TOPIC]: defaultHandler,
  [WorkflowStateType.SQS_QUEUE]: defaultHandler,
  [WorkflowStateType.WARMER_TRIGGER]: defaultHandler
};

async function maybeMkdir(fs: PromiseFsClient, path: string) {
  try {
    await fs.promises.lstat(path);
  } catch (e) {
    await fs.promises.mkdir(path);
  }
}

export async function saveProjectToRepo(fs: PromiseFsClient, dir: string, project: RefineryProject) {
  await maybeMkdir(fs, Path.join(dir, GLOBAL_BASE_PATH));

  // clean repo of all existing files and dirs
  let dirsToRemove = await git.walk({
    fs,
    dir,
    trees: [WORKDIR()],
    map: async (filename: string, entries: Array<WalkerEntry> | null) => {
      if (filename.startsWith('.git')) {
        return null;
      }

      if (entries && (await entries[0].type()) === 'tree') {
        return filename;
      }

      await fs.promises.unlink(Path.join(dir, filename));
      return null;
    }
  });
  dirsToRemove.reverse();

  await Promise.all(
    dirsToRemove.map(async (dirToRemove: string | null) => {
      if (dirToRemove !== null && dirToRemove !== '.') {
        try {
          await fs.promises.rmdir(Path.join(dir, dirToRemove));
        } catch (e) {
          console.log(Path.join(dir, dirToRemove), e);
        }
      }
    })
  );

  await maybeMkdir(fs, Path.join(dir, GLOBAL_BASE_PATH));

  const nodeToWorkflowState = await project.workflow_states.reduce(async (workflowStates, w: WorkflowState) => {
    const awaitedWorkflowStates = await workflowStates;
    const path = await workflowStateActions[w.type](fs, dir, project, w);
    return {
      ...awaitedWorkflowStates,
      [w.id]: {
        workflow_state: w,
        path: path
      }
    };
  }, Promise.resolve({} as Record<string, { workflow_state: WorkflowState; path: string }>));

  // set project's workflow states to ones that were not handled by compilation
  const newWorkflowStates = Object.keys(nodeToWorkflowState).reduce((newWorkflowStates, nodeId) => {
    if (nodeToWorkflowState[nodeId].path === '') {
      newWorkflowStates.push(nodeToWorkflowState[nodeId].workflow_state);
    }
    return newWorkflowStates;
  }, [] as WorkflowState[]);

  const sharedFilesPath = Path.join(dir, GLOBAL_BASE_PATH, PROJECT_SHARED_FILES_DIR);
  await maybeMkdir(fs, sharedFilesPath);
  const sharedFileLookup = await project.workflow_files.reduce(async (lookup, file) => {
    const awaitedLookup = await lookup;
    const sharedFileFilename = Path.join(sharedFilesPath, file.name);
    await fs.promises.writeFile(sharedFileFilename, file.body);

    // need to determine relative path to this file
    const sharedFileFilenameFromRoot = Path.join(GLOBAL_BASE_PATH, PROJECT_SHARED_FILES_DIR, file.name);

    return {
      ...awaitedLookup,
      [file.id]: {
        file: file,
        path: sharedFileFilenameFromRoot
      }
    };
  }, Promise.resolve({} as Record<string, { file: WorkflowFile; path: string }>));
  // we have handled workflow_files
  const newWorkflowFiles: WorkflowFile[] = [];

  await Promise.all(
    project.workflow_file_links
      .filter(f => f.type === 'shared_file_link')
      .map(async fileLink => {
        const sharedFile = sharedFileLookup[fileLink.file_id];

        const lambdaSharedFilePath = Path.join(nodeToWorkflowState[fileLink.node].path, LAMBDA_SHARED_FILES_DIR);
        await maybeMkdir(fs, lambdaSharedFilePath);
        const sharedFileLinkPath = Path.join(lambdaSharedFilePath, sharedFile.file.name);

        // we go up from the 'shared_folders', <lambda block folder>, 'lambda' to get to root
        const relativeSharedFilePath = Path.join('..', '..', '..', '..', sharedFile.path);

        if (fs.promises.symlink) {
          await fs.promises.symlink(relativeSharedFilePath, sharedFileLinkPath);
        }
      })
  );

  const projectFolder = Path.join(dir, GLOBAL_BASE_PATH, PROJECTS_CONFIG_FOLDER);

  // we have handled workflow_file_links
  const newWorkflowFileLinks: WorkflowFileLink[] = [];

  const newProject: RefineryProject = {
    ...project,
    workflow_states: newWorkflowStates,
    workflow_files: newWorkflowFiles,
    workflow_file_links: newWorkflowFileLinks
  };

  await maybeMkdir(fs, projectFolder);

  const projectConfig = Path.join(projectFolder, `${project.project_id}.yaml`);

  // TODO we should enforce an ordering of these values so that we don't get modifications every time we write the file
  await writeConfig(fs, projectConfig, newProject);
}