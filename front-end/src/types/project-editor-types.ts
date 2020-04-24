import { VueConstructor } from 'vue';
import { ProjectConfig, RefineryProject, SupportedLanguage } from '@/types/graph';
import { DeploymentException } from '@/types/api-types';
import { CssStyleDeclaration } from 'cytoscape';

export enum SIDEBAR_PANE {
  // Project Editor
  addBlock = 'addBlock',
  addSavedBlock = 'addSavedBlock',
  addTransition = 'addTransition',
  allBlocks = 'allBlocks',
  allVersions = 'allVersions',
  exportProject = 'exportProject',
  saveProject = 'saveProject',
  deployProject = 'deployProject',
  editBlock = 'editBlock',
  editTransition = 'editTransition',
  runEditorCodeBlock = 'runEditorCodeBlock',
  sharedFiles = 'sharedFiles',
  editSharedFile = 'editSharedFile',
  editSharedFileLinks = 'editSharedFileLinks',
  addingSharedFileLink = 'addingSharedFileLink',
  codeBlockSharedFiles = 'codeBlockSharedFiles',
  viewSharedFile = 'viewSharedFile',
  viewReadme = 'viewReadme',
  editReadme = 'editReadme',

  // Deployment Viewer
  viewApiEndpoints = 'viewApiEndpoints',
  viewExecutions = 'viewExecutions',
  destroyDeploy = 'destroyDeploy',
  viewDeployedBlock = 'viewDeployedBlock',
  viewDeployedBlockLogs = 'viewDeployedBlockLogs',
  viewDeployedTransition = 'viewDeployedTransition',
  runDeployedCodeBlock = 'runDeployedCodeBlock'
}

export enum PANE_POSITION {
  left = 'left',
  right = 'right'
  // TODO: This is gonna be so lit
  // float = 'float'
}

export type LeftSidebarPaneState = { [key in SIDEBAR_PANE]: {} };

export interface UpdateLeftSidebarPaneStateMutation {
  leftSidebarPane: SIDEBAR_PANE;
  position: PANE_POSITION;
  newState: {};
}

export interface ActivePaneState {
  type: SIDEBAR_PANE;
  position: PANE_POSITION;
  state: {};
}

export type ActiveSidebarPaneToContainerMapping = { [key in SIDEBAR_PANE]: VueConstructor };

export interface OpenProjectMutation {
  project: RefineryProject | null;
  config: ProjectConfig | null;
  markAsDirty: boolean;
}

export interface FormProps {
  [index: string]: any;

  idPrefix: string;
  description: string;
  placeholder: string;
  name: string;
  type?: string;
  readonly: boolean;
  disabled: boolean;
  value: any;
  on: { change?: Function; update?: Function; blur?: Function };
}

export type SupportedLanguageToAceLang = { [key in SupportedLanguage]: string };

export interface MonacoLanguageLookup extends SupportedLanguageToAceLang {
  text: 'text';
  json: 'json';
  markdown: 'markdown';
}

export const languageToAceLangMap: MonacoLanguageLookup = {
  [SupportedLanguage.NODEJS_8]: 'javascript',
  [SupportedLanguage.NODEJS_10]: 'javascript',
  [SupportedLanguage.NODEJS_1020]: 'javascript',
  [SupportedLanguage.PYTHON_2]: 'python',
  [SupportedLanguage.PYTHON_3]: 'python',
  [SupportedLanguage.GO1_12]: 'go',
  [SupportedLanguage.PHP7]: 'php',
  [SupportedLanguage.RUBY2_6_4]: 'ruby',
  text: 'text',
  json: 'json',
  markdown: 'markdown'
};

export type LanguageToBaseRepoURL = { [key in SupportedLanguage]: string | null };

export const LanguageToBaseRepoURLMap: LanguageToBaseRepoURL = {
  [SupportedLanguage.NODEJS_8]: 'https://www.npmjs.com',
  [SupportedLanguage.NODEJS_10]: 'https://www.npmjs.com',
  [SupportedLanguage.NODEJS_1020]: 'https://www.npmjs.com',
  [SupportedLanguage.PYTHON_2]: 'https://pypi.org',
  [SupportedLanguage.PYTHON_3]: 'https://pypi.org',
  [SupportedLanguage.GO1_12]: null,
  [SupportedLanguage.PHP7]: 'https://packagist.org',
  [SupportedLanguage.RUBY2_6_4]: 'https://rubygems.org'
};

export type LanguageToLibraryRepoURL = { [key in SupportedLanguage]: string | null };

export const LanguageToLibraryRepoURLMap: LanguageToLibraryRepoURL = {
  [SupportedLanguage.NODEJS_8]: LanguageToBaseRepoURLMap[SupportedLanguage.NODEJS_8] + '/package/',
  [SupportedLanguage.NODEJS_10]: LanguageToBaseRepoURLMap[SupportedLanguage.NODEJS_8] + '/package/',
  [SupportedLanguage.NODEJS_1020]: LanguageToBaseRepoURLMap[SupportedLanguage.NODEJS_8] + '/package/',
  [SupportedLanguage.PYTHON_3]: LanguageToBaseRepoURLMap[SupportedLanguage.PYTHON_3] + '/project/',
  [SupportedLanguage.PYTHON_2]: LanguageToBaseRepoURLMap[SupportedLanguage.PYTHON_2] + '/project/',
  [SupportedLanguage.GO1_12]: null,
  [SupportedLanguage.PHP7]: LanguageToBaseRepoURLMap[SupportedLanguage.PHP7] + '/packages/psr/',
  [SupportedLanguage.RUBY2_6_4]: LanguageToBaseRepoURLMap[SupportedLanguage.RUBY2_6_4] + '/gems/'
};

export interface DeployProjectParams {
  project: RefineryProject;
  projectConfig: ProjectConfig;
}

export type DeployProjectResult = DeploymentException[] | null;
