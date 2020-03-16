const program = require('commander');
import { LambdaWorkflowState, RefineryProject, WorkflowFile, WorkflowState, WorkflowStateType } from '@/types/graph';
import {
  convertProjectDownloadZipConfigToFileList,
  createDownloadZipConfig,
  languageToFileExtension
} from '@/utils/project-debug-utils';
const Path = require('path');
const fs = require('fs');
const slugify = require('slugify');

function getFolderName(name: string) {
  return slugify(name).toLowerCase();
}

function deleteFolderRecursive(path: string) {
  fs.readdirSync(path).forEach((file: string, index: number) => {
    const curPath = Path.join(path, file);
    if (fs.lstatSync(curPath).isDirectory()) {
      deleteFolderRecursive(curPath);
    } else {
      fs.unlinkSync(curPath);
    }
  });
  fs.rmdirSync(path);
}

function resetDir(dir: string) {
  if (fs.existsSync(dir)) {
    deleteFolderRecursive(dir);
  }
  fs.mkdirSync(dir);
}

function makeDirExist(dir: string) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir);
  }
}

function lambdaConfigReplacer(key: string, value: any) {
  if (key === 'code') {
    return undefined;
  }
  return value;
}

function writeConfig(out: string, data: any, replacer?: (this: any, key: string, value: any) => any) {
  const serializedConfig = JSON.stringify(data, replacer, 2);
  fs.writeFileSync(out, serializedConfig);
}

function handleLambda(projectDir: string, project: RefineryProject, workflowState: WorkflowState): string | null {
  const lambda = workflowState as LambdaWorkflowState;

  const typePath = Path.join(projectDir, getFolderName(workflowState.type));
  makeDirExist(typePath);

  const blockDir = getFolderName(lambda.name);
  const lambdaDir = Path.join(typePath, blockDir);
  resetDir(lambdaDir);

  const config = createDownloadZipConfig(project, lambda);
  const filesToZip = convertProjectDownloadZipConfigToFileList(config);

  filesToZip.forEach(file => {
    const path = Path.join(lambdaDir, file.fileName);
    fs.writeFileSync(path, file.contents);
  });

  const lambdaConfig = Path.join(lambdaDir, 'config.json');
  writeConfig(lambdaConfig, lambda, lambdaConfigReplacer);

  return lambdaDir;
}

function defaultHandler(projectDir: string, project: RefineryProject, workflowState: WorkflowState): null {
  return null;
}

const workflowStateActions: Record<
  WorkflowStateType,
  (projectDir: string, project: RefineryProject, e: WorkflowState) => string | null
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

function saveProjectToRepo(projectDir: string, project: RefineryProject) {
  resetDir(projectDir);

  const nodeToWorkflowState = project.workflow_states.reduce(
    (workflowStates, w: WorkflowState) => {
      const path = workflowStateActions[w.type](projectDir, project, w);
      if (path) {
        return {
          ...workflowStates,
          [w.id]: path
        };
      }
      return workflowStates;
    },
    {} as Record<string, string>
  );

  const sharedFilesPath = Path.join(projectDir, 'shared-files');
  makeDirExist(sharedFilesPath);
  const sharedFileLookup = project.workflow_files.reduce(
    (lookup, file) => {
      const sharedFileFilename = Path.join(sharedFilesPath, file.name) as string;
      fs.writeFileSync(sharedFileFilename, file.body);
      return {
        ...lookup,
        [file.id]: {
          file: file,
          path: sharedFileFilename
        }
      };
    },
    {} as Record<string, { file: WorkflowFile; path: string }>
  );

  project.workflow_file_links
    .filter(f => f.type == 'shared_file_link')
    .forEach(fileLink => {
      const sharedFile = sharedFileLookup[fileLink.file_id];
      const sharedFileLinkPath = Path.join(nodeToWorkflowState[fileLink.node], sharedFile.file.name);
      fs.linkSync(sharedFile.path, sharedFileLinkPath);

      // TODO update dockerfile?
    });

  /* ignore this for now
  project.workflow_states = newWorkflowStates;

  const projectConfig = Path.join(projectDir, 'project.json');
  writeConfig(projectConfig, project);
  */
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

program.command('lint <dir>').action(lint);

program.parse(process.argv);
