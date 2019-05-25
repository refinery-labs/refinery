import {BaseRefineryResource, CyElements, CyStyle, RefineryProject} from '@/types/graph';
import {LayoutOptions} from 'cytoscape';
import cytoscape from '@/components/CytoscapeGraph';
import {ProjectSearchResult} from '@/types/api-types';

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

export interface ProjectViewState {
  openedProject: RefineryProject | null,
  selectedResource: BaseRefineryResource | null,
  cytoscapeElements: CyElements | null,
  cytoscapeStyle: CyStyle | null,
  cytoscapeLayoutOptions: LayoutOptions | null,
  cytoscapeConfig: cytoscape.CytoscapeOptions | null
}

export interface AllProjectsState {
  availableProjects: ProjectSearchResult[],
  searchBox: string,
  isSearching: boolean
}
