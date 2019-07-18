import { baseLinks } from '@/constants/router-constants';
import { MenuItemList, NavbarItem } from '@/types/layout-types';
import { SIDEBAR_PANE } from '@/types/project-editor-types';

export const GlobalNavMenuItems: MenuItemList = [
  {
    heading: 'Global Navigation',
    translate: 'sidebar.heading.HEADER'
  },
  {
    name: 'Home',
    path: baseLinks.home,
    icon: 'icon-home',
    translate: 'global.nav.HOME'
  },
  {
    name: 'All Projects',
    path: baseLinks.projects,
    icon: 'icon-chemistry',
    translate: 'global.nav.PROJECTS'
  },
  /*  {
    name: 'Marketplace',
    path: baseLinks.marketplace,
    icon: 'icon-basket',
    translate: 'global.nav.MARKETPLACE'
  },
  {
    name: 'Settings',
    path: baseLinks.settings,
    icon: 'icon-settings',
    translate: 'global.nav.SETTINGS'
  },
  {
    name: 'About',
    path: baseLinks.about,
    icon: 'icon-info',
    translate: 'global.nav.ABOUT'
  },*/
  {
    name: 'Billing',
    path: baseLinks.billing,
    icon: 'icon-wallet',
    translate: 'global.nav.BILLINGx'
  },
  {
    name: 'Help',
    path: baseLinks.help,
    icon: 'icon-question',
    translate: 'global.nav.HELP'
  }
];

export type EditorPaneTypeToName = { [key in SIDEBAR_PANE]: string };

export const paneTypeToNameLookup: EditorPaneTypeToName = {
  [SIDEBAR_PANE.addBlock]: 'Add Block',
  [SIDEBAR_PANE.addSavedBlock]: 'Add Saved Block',
  [SIDEBAR_PANE.addTransition]: 'Add Transition',
  [SIDEBAR_PANE.allBlocks]: 'All Blocks',
  [SIDEBAR_PANE.allVersions]: 'All Versions',
  [SIDEBAR_PANE.exportProject]: 'Share Project',
  [SIDEBAR_PANE.saveProject]: 'Save Project',
  [SIDEBAR_PANE.deployProject]: 'Deploy Project',
  [SIDEBAR_PANE.editBlock]: 'Edit Block',
  [SIDEBAR_PANE.editTransition]: 'Edit Transition',
  [SIDEBAR_PANE.viewApiEndpoints]: 'API Endpoints',
  [SIDEBAR_PANE.viewExecutions]: 'Block Executions',
  [SIDEBAR_PANE.destroyDeploy]: 'Destroy Deploy',
  [SIDEBAR_PANE.viewDeployedBlock]: 'Inspect Deployed Block',
  [SIDEBAR_PANE.viewDeployedBlockLogs]: 'Block Execution Logs',
  [SIDEBAR_PANE.viewDeployedTransition]: 'Inspect Deployed Transition',
  [SIDEBAR_PANE.runEditorCodeBlock]: 'Code Runner',
  [SIDEBAR_PANE.runDeployedCodeBlock]: 'Code Runner'
};

export const paneTypeToWindowNameLookup: EditorPaneTypeToName = {
  ...paneTypeToNameLookup,
  [SIDEBAR_PANE.addBlock]: `Click to ${paneTypeToNameLookup[SIDEBAR_PANE.addBlock]}`,
  [SIDEBAR_PANE.runEditorCodeBlock]: 'Execute Editor Code Block',
  [SIDEBAR_PANE.runDeployedCodeBlock]: 'Execute Deployed Code Block'
};

function makeSidebarMenuItem(type: SIDEBAR_PANE, icon: string, translate: string, variant: string): NavbarItem {
  return {
    name: paneTypeToNameLookup[type],
    icon,
    translate: `sidebar.nav.${translate}`,
    label: paneTypeToNameLookup[type],
    buttonVariant: variant,
    editorPane: type
  };
}

// TODO: Make a small helper to generate these instead of copy-pasting
export const SidebarMenuItems: NavbarItem[] = [
  makeSidebarMenuItem(SIDEBAR_PANE.addBlock, 'icon-plus', 'sidebar.nav.ADD_BLOCK', 'outline-primary'),
  makeSidebarMenuItem(SIDEBAR_PANE.addTransition, 'icon-cursor-move', 'sidebar.nav.ADD_TRANSITION', 'outline-primary'),
  makeSidebarMenuItem(SIDEBAR_PANE.runEditorCodeBlock, 'icon-control-play', 'RUN_CODE_BLOCK', 'outline-success'),
  // makeSidebarMenuItem(SIDEBAR_PANE.allBlocks, 'icon-grid', 'sidebar.nav.ALL_BLOCKS', 'outline-info'),
  // makeSidebarMenuItem(SIDEBAR_PANE.allVersions, 'icon-chart', 'sidebar.nav.ALL_VERSIONS', 'outline-info'),
  makeSidebarMenuItem(SIDEBAR_PANE.exportProject, 'icon-cloud-download', 'sidebar.nav.EXPORT_PROJECT', 'outline-info'),
  makeSidebarMenuItem(SIDEBAR_PANE.saveProject, 'far fa-save', 'sidebar.nav.SAVE_PROJECT', 'success'),
  makeSidebarMenuItem(SIDEBAR_PANE.deployProject, 'icon-cloud-upload', 'sidebar.nav.DEPLOY_PROJECT', 'primary')
];

export const DeploymentSidebarMenuItems: NavbarItem[] = [
  // TODO: Finish this functionality
  // makeSidebarMenuItem(SIDEBAR_PANE.viewApiEndpoints, 'icon-list', 'sidebar.nav.VIEW_API_ENDPOINTS', 'outline-info'),
  makeSidebarMenuItem(SIDEBAR_PANE.viewExecutions, 'icon-organization', 'sidebar.nav.VIEW_EXECUTIONS', 'outline-info'),
  makeSidebarMenuItem(SIDEBAR_PANE.runDeployedCodeBlock, 'icon-control-play', 'RUN_CODE_BLOCK', 'outline-success'),
  makeSidebarMenuItem(SIDEBAR_PANE.destroyDeploy, 'icon-ban', 'sidebar.nav.DESTROY_DEPLOY', 'danger')
];
