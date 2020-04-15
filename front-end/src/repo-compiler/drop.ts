const program = require('commander');
import {
  LambdaWorkflowState,
  RefineryProject,
  WorkflowFile,
  WorkflowFileLink,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { convertProjectDownloadZipConfigToFileList, createDownloadZipConfig } from '@/utils/project-debug-utils';
import LightningFS from '@isomorphic-git/lightning-fs';
import git, { WORKDIR, PromiseFsClient, WalkerEntry, StatusRow, PushResult } from 'isomorphic-git';
import http from '@/repo-compiler/git-http';
import Path from 'path';
import slugify from 'slugify';
import yaml from 'js-yaml';

function getFolderName(name: string) {
  return slugify(name).toLowerCase();
}

async function writeConfig(fs: PromiseFsClient, out: string, data: any) {
  const serializedConfig = yaml.safeDump(data);
  await fs.promises.writeFile(out, serializedConfig);
}

async function getLambdaDir(fs: PromiseFsClient, lambdaDir: string, lambdaId: string): Promise<string> {
  if (await fs.promises.stat(lambdaDir).catch(() => false)) {
    const firstPartOfId = lambdaId.split('-')[0];
    return `${lambdaDir}-${firstPartOfId}`;
  }
  return lambdaDir;
}

async function handleLambda(
  fs: PromiseFsClient,
  projectDir: string,
  project: RefineryProject,
  workflowState: WorkflowState
): Promise<string> {
  const lambda = workflowState as LambdaWorkflowState;

  const typePath = Path.join(projectDir, getFolderName(workflowState.type));
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
  if (!(await fs.promises.stat(path).catch(() => false))) {
    await fs.promises.mkdir(path).catch((e: Error) => console.error('error while mkdir: ' + path + ' ' + e));
  }
}

export async function saveProjectToRepo(
  fs: PromiseFsClient,
  dir: string,
  project: RefineryProject
): Promise<Array<StatusRow>> {
  // TODO we shouldn't need to wipe this directory if we already pulled from it when compiling the repo
  // TODO we probably just want to fetch get objects and not populate the fs (i think this is possible with git)

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
        await fs.promises.rmdir(Path.join(dir, dirToRemove));
      }
    })
  );

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
  const newWorkflowStates = Object.keys(nodeToWorkflowState).reduce(
    (newWorkflowStates, nodeId) => {
      if (nodeToWorkflowState[nodeId].path === '') {
        newWorkflowStates.push(nodeToWorkflowState[nodeId].workflow_state);
      }
      return newWorkflowStates;
    },
    [] as WorkflowState[]
  );

  const sharedFilesRoot = 'shared-files';
  const sharedFilesPath = Path.join(dir, sharedFilesRoot);
  await maybeMkdir(fs, sharedFilesPath);
  const sharedFileLookup = await project.workflow_files.reduce(async (lookup, file) => {
    const awaitedLookup = await lookup;
    const sharedFileFilename = Path.join(sharedFilesPath, file.name);
    await fs.promises.writeFile(sharedFileFilename, file.body);

    // need to determine relative path to this file
    const sharedFileFilenameFromRoot = Path.join(sharedFilesRoot, file.name);

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
      .filter(f => f.type == 'shared_file_link')
      .map(async fileLink => {
        const sharedFile = sharedFileLookup[fileLink.file_id];

        const lambdaSharedFilePath = Path.join(nodeToWorkflowState[fileLink.node].path, 'shared_files');
        await maybeMkdir(fs, lambdaSharedFilePath);
        const sharedFileLinkPath = Path.join(lambdaSharedFilePath, sharedFile.file.name);

        // we go up from the 'shared_folders', <lambda block folder>, 'lambda' to get to root
        const relativeSharedFilePath = Path.join('..', '..', '..', sharedFile.path);

        if (fs.promises.symlink) {
          await fs.promises.symlink(relativeSharedFilePath, sharedFileLinkPath);
        }
      })
  );

  // we have handled workflow_file_links
  const newWorkflowFileLinks: WorkflowFileLink[] = [];

  const newProject: RefineryProject = {
    ...project,
    workflow_states: newWorkflowStates,
    workflow_files: newWorkflowFiles,
    workflow_file_links: newWorkflowFileLinks
  };

  const projectConfig = Path.join(dir, 'project.yaml');
  await writeConfig(fs, projectConfig, newProject);

  return await git.statusMatrix({
    fs,
    dir
  });
}

export async function commitAndPushToRepo(
  fs: PromiseFsClient,
  dir: string,
  branch: string,
  force: boolean
): Promise<PushResult> {
  await git.add({ fs, dir, filepath: '.' });

  await git.commit({
    fs,
    dir,
    author: {
      name: 'Refinery Bot',
      email: 'donotreply@refinery.io'
    },
    message: 'compiled project from Refinery web'
  });

  return await git.push({
    fs,
    http,
    dir,
    remote: 'origin',
    remoteRef: branch,
    corsProxy: `${process.env.VUE_APP_API_HOST}/api/v1/github/proxy`,
    force
  });
}
/*

interface NewBlockOptions {
  language: string;
}

function newBlock(projectdir: string, type: string, name: string, options: NewBlockOptions) {
  if (type === 'lambda') {
    const lambdaLanguage = options.language as SupportedLanguage;
    if (!Object.values(SupportedLanguage).includes(lambdaLanguage)) {
      console.error('Lambda block language ${lambdaLanguage} not supported');
      return;
    }

    const blockName = getFolderName(name);

    const lambdaConfig: ProjectDownloadZipConfig = {
      inputData: '{}',
      backpackData: '{}',
      blockCode: DEFAULT_LANGUAGE_CODE[lambdaLanguage],
      blockLanguage: lambdaLanguage,
      metadata: {
        projectName: '',
        projectId: '',
        projectVersion: 1,
        blockName: blockName,
        blockId: '',
        exportedTimestamp: 0,
        version: ''
      }
    };

    const blockPath = Path.join(projectdir, 'lambda', blockName);
    resetDir(blockPath);

    const lambdaFiles = convertProjectDownloadZipConfigToFileList(lambdaConfig);
    lambdaFiles.forEach(file => {
      const path = Path.join(blockPath, file.fileName);
      fs.writeFileSync(path, file.contents);
    });
  } else {
    console.error('Unsupported type: ${type}');
  }
}


function load(config: string) {
  const configData = fs.readFileSync(config, 'utf8');
  const projectJSON = JSON.parse(configData);
  const project = projectJSON as RefineryProject;

  const projectDir = getFolderName(project.name);
  saveProjectToRepo(projectDir, project);
}

function lint(dir: string) {
  if (!fs.existsSync(dir)) {
    console.error(`Unable to find dir ${dir}`);
    return;
  }
}

program.command('load <config>').action(load);

program
  .command('new <projectdir> <type> <name>')
  .option('--language <language>')
  .action(newBlock);

program.command('lint <dir>').action(lint);

program.parse(process.argv);

 */
