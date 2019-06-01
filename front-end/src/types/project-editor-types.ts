import {VueConstructor} from 'vue';
import {ProjectConfig, RefineryProject} from '@/types/graph';

export enum LEFT_SIDEBAR_PANE {
  addBlock = "addBlock",
  addTransition = "addTransition",
  allBlocks = "allBlocks",
  allVersions = "allVersions",
  saveProject = "saveProject",
  deployProject = "deployProject"
}

export type LeftSidebarPaneState = {
  [key in LEFT_SIDEBAR_PANE]: {}
}

export interface UpdateLeftSidebarPaneStateMutation {
  leftSidebarPane: LEFT_SIDEBAR_PANE,
  newState: {}
}

export type ActiveLeftSidebarPaneToContainerMapping = {
  [key in LEFT_SIDEBAR_PANE]: VueConstructor
}

export interface OpenProjectMutation {
  project: RefineryProject,
  config: ProjectConfig | null,
  markAsDirty: boolean
}
