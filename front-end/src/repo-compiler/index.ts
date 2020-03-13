const program = require('commander');
import { LambdaWorkflowState, RefineryProject, WorkflowState, WorkflowStateType } from '@/types/graph';
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

function handleLambda(
  projectDir: string,
  project: RefineryProject,
  workflowState: WorkflowState
): WorkflowState | null {
  const lambda = workflowState as LambdaWorkflowState;

  const blockDir = getFolderName(lambda.name);
  const lambdaDir = Path.join(projectDir, blockDir);
  resetDir(lambdaDir);

  const config = createDownloadZipConfig(project, lambda);
  const filesToZip = convertProjectDownloadZipConfigToFileList(config);

  filesToZip.forEach(file => {
    const path = Path.join(lambdaDir, file.fileName);
    fs.writeFileSync(path, file.contents);
  });

  const lambdaConfig = Path.join(lambdaDir, 'config.json');
  writeConfig(lambdaConfig, lambda, lambdaConfigReplacer);

  return null;
}

function defaultHandler(projectDir: string, project: RefineryProject, workflowState: WorkflowState): WorkflowState {
  return workflowState;
}

const workflowStateActions: Record<
  WorkflowStateType,
  (projectDir: string, project: RefineryProject, e: WorkflowState) => WorkflowState | null
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

  // any workflow state that is not explicitly handled will be
  // dropped into the main config
  const newWorkflowStates = project.workflow_states.reduce(
    (workflowStates: WorkflowState[], w: WorkflowState) => {
      const workflowState = workflowStateActions[w.type](projectDir, project, w);
      if (workflowState) {
        workflowStates.push(workflowState);
      }
      return workflowStates;
    },
    [] as WorkflowState[]
  );

  project.workflow_states = newWorkflowStates;

  const projectConfig = Path.join(projectDir, 'project.json');
  writeConfig(projectConfig, project);
}

function load(config: string) {
  const configData = fs.readFileSync(config, 'utf8');
  const projectJSON = JSON.parse(configData);
  const project = projectJSON as RefineryProject;

  const projectDir = getFolderName(project.name);
  saveProjectToRepo(projectDir, project);
}

function save(dir: string) {}

program
  .command('load <config>')
  //.option('-r, --recursive', 'Remove recursively')
  .action(load);

program
  .command('save <dir>')
  //.option('-r, --recursive', 'Remove recursively')
  .action(save);

program.parse(process.argv);
