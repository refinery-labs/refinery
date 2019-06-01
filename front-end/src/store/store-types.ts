import {
  BaseRefineryResource,
  CyElements,
  CyStyle, ProjectConfig,
  RefineryProject,
  WorkflowRelationshipType,
  WorkflowState
} from '@/types/graph';
import {LayoutOptions} from 'cytoscape';
import cytoscape from '@/components/CytoscapeGraph';
import {SearchSavedProjectsResult} from '@/types/api-types';
import {LeftSidebarPaneState, LEFT_SIDEBAR_PANE} from '@/types/project-editor-types';
import {ValidTransitionConfig} from '@/constants/project-editor-constants';

export interface RootState {
  setting: UserInterfaceState,
  project: ProjectViewState,
  allProjects: AllProjectsState
}

export enum UserInterfaceSettings {
  isFixed = 'isFixed',
  isGlobalNavCollapsed = 'isGlobalNavCollapsed',
  isGlobalNavClosing = 'isGlobalNavClosing',
  isSidebarCollapsed = 'isSidebarCollapsed',
  isBoxed = 'isBoxed',
  isFloat = 'isFloat',
  asideHover = 'asideHover',
  asideScrollbar = 'asideScrollbar',
  isCollapsedText = 'isCollapsedText',
  offsidebarOpen = 'offsidebarOpen',
  asideToggled = 'asideToggled',
  showUserBlock = 'showUserBlock',
  horizontal = 'horizontal',
  useFullLayout = 'useFullLayout',
  hiddenFooter = 'hiddenFooter'
}

export interface UserInterfaceState {
  /* Layout fixed. Scroll content only */
  [UserInterfaceSettings.isFixed]?: boolean,
  /* Global Nav collapsed */
  [UserInterfaceSettings.isGlobalNavCollapsed]?: boolean,
  /* Global Nav closing, fires when nav is closed */
  [UserInterfaceSettings.isGlobalNavClosing]?: boolean,
  /* Sidebar collapsed */
  [UserInterfaceSettings.isSidebarCollapsed]?: boolean,
  /* Boxed layout */
  [UserInterfaceSettings.isBoxed]?: boolean,
  /* Floating sidebar */
  [UserInterfaceSettings.isFloat]?: boolean,
  /* Sidebar show menu on hover only */
  [UserInterfaceSettings.asideHover]?: boolean,
  /* Show sidebar scrollbar (dont' hide it) */
  [UserInterfaceSettings.asideScrollbar]?: boolean,
  /* Sidebar collapsed with big icons and text */
  [UserInterfaceSettings.isCollapsedText]?: boolean,
  /* Toggle for the offsidebar */
  [UserInterfaceSettings.offsidebarOpen]?: boolean,
  /* Toggle for the sidebar offcanvas (mobile) */
  [UserInterfaceSettings.asideToggled]?: boolean,
  /* Toggle for the sidebar user block */
  [UserInterfaceSettings.showUserBlock]?: boolean,
  /* Enables layout horizontal */
  [UserInterfaceSettings.horizontal]?: boolean,
  /* Full size layout */
  [UserInterfaceSettings.useFullLayout]?: boolean,
  /* Hide footer */
  [UserInterfaceSettings.hiddenFooter]?: boolean
}

export interface AvailableTransition {
  valid: boolean,
  transitionConfig: ValidTransitionConfig,
  fromNode: WorkflowState,
  toNode: WorkflowState,
  simple: boolean
}

export interface AvailableTransitionsByType {
  simple: AvailableTransition[],
  complex: AvailableTransition[]
}

export interface ProjectViewState {
  openedProject: RefineryProject | null,
  openedProjectConfig: ProjectConfig | null,
  
  // Disgusting backup copies so that we can revert or whatever later
  openedProjectOriginal: RefineryProject | null,
  openedProjectConfigOriginal: ProjectConfig | null,
  
  isLoadingProject: boolean,
  isProjectBusy: boolean,
  hasProjectBeenModified: boolean,
  
  leftSidebarPaneState: LeftSidebarPaneState,
  activeLeftSidebarPane: LEFT_SIDEBAR_PANE | null,
  
  // Shared Graph State
  selectedResource: string | null,
  // If this is "null" then it enables all elements
  enabledGraphElements: string[] | null,
  
  // Cytoscape Specific state
  cytoscapeElements: CyElements | null,
  cytoscapeStyle: CyStyle | null,
  cytoscapeLayoutOptions: LayoutOptions | null,
  cytoscapeConfig: cytoscape.CytoscapeOptions | null,
  
  // Add Block Pane
  selectedBlockIndex: number | null,
  
  // Add Transition Pane
  isAddingTransitionCurrently: boolean,
  newTransitionTypeSpecifiedInAddFlow: WorkflowRelationshipType | null,
  availableTransitions: AvailableTransitionsByType | null
}

export interface AllProjectsState {
  availableProjects: SearchSavedProjectsResult[],
  searchBoxText: string,
  isSearching: boolean
}
