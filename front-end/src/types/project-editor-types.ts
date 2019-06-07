import { VueConstructor } from 'vue';
import { ProjectConfig, RefineryProject } from '@/types/graph';

export enum SIDEBAR_PANE {
  addBlock = 'addBlock',
  addTransition = 'addTransition',
  allBlocks = 'allBlocks',
  allVersions = 'allVersions',
  saveProject = 'saveProject',
  deployProject = 'deployProject',
  editBlock = 'editBlock',
  editTransition = 'editTransition'
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
