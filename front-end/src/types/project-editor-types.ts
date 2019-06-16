import { VueConstructor } from 'vue';
import { ProjectConfig, RefineryProject, SupportedLanguage } from '@/types/graph';

export enum SIDEBAR_PANE {
  // Project Editor
  addBlock = 'addBlock',
  addTransition = 'addTransition',
  allBlocks = 'allBlocks',
  allVersions = 'allVersions',
  exportProject = 'exportProject',
  saveProject = 'saveProject',
  deployProject = 'deployProject',
  editBlock = 'editBlock',
  editTransition = 'editTransition',
  runEditorCodeBlock = 'runEditorCodeBlock',

  // Deployment Viewer
  viewApiEndpoints = 'viewApiEndpoints',
  viewExecutions = 'viewExecutions',
  destroyDeploy = 'destroyDeploy',
  viewDeployedBlock = 'viewDeployedBlock',
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
  project: RefineryProject;
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
  value: any;
  on: { change: Function };
}

export type LanguageToAceLang = { [key in SupportedLanguage]: string };

export const languageToAceLangMap: LanguageToAceLang = {
  [SupportedLanguage.NODEJS_8]: 'javascript',
  [SupportedLanguage.PYTHON_2]: 'python',
  [SupportedLanguage.GO1_12]: 'golang',
  [SupportedLanguage.PHP7]: 'php'
};

export type LanguageToBaseRepoURL = { [key in SupportedLanguage]: string | null };

export const LanguageToBaseRepoURLMap: LanguageToBaseRepoURL = {
  [SupportedLanguage.NODEJS_8]: 'https://www.npmjs.com',
  [SupportedLanguage.PYTHON_2]: 'https://pypi.org',
  [SupportedLanguage.GO1_12]: null,
  [SupportedLanguage.PHP7]: 'https://packagist.org'
};

export type LanguageToLibraryRepoURL = { [key in SupportedLanguage]: string | null };

export const LanguageToLibraryRepoURLMap: LanguageToLibraryRepoURL = {
  [SupportedLanguage.NODEJS_8]: LanguageToBaseRepoURLMap[SupportedLanguage.NODEJS_8] + '/package/',
  [SupportedLanguage.PYTHON_2]: LanguageToBaseRepoURLMap[SupportedLanguage.PYTHON_2] + '/project/',
  [SupportedLanguage.GO1_12]: null,
  [SupportedLanguage.PHP7]: LanguageToBaseRepoURLMap[SupportedLanguage.PHP7] + '/packages/psr/'
};
