import { VueConstructor } from 'vue';
import {ProjectConfig, RefineryProject, SupportedLanguage} from '@/types/graph';

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

  // Deployment Viewer
  viewApiEndpoints = 'viewApiEndpoints',
  viewExecutions = 'viewExecutions',
  viewDeployedBlock = 'viewDeployedBlock',
  viewDeployedTransition = 'viewDeployedTransition'
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