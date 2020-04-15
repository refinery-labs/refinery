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
    translate: 'global.nav.HOME',
    authenticated: true
  },
  {
    name: 'All Projects',
    path: baseLinks.projects,
    icon: 'icon-chemistry',
    translate: 'global.nav.PROJECTS',
    authenticated: true
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
    translate: 'global.nav.BILLING',
    authenticated: true
  },
  {
    name: 'Documentation',
    path: baseLinks.documentation,
    external: true,
    icon: 'icon-book-open',
    translate: 'global.nav.DOCUMENTATION',
    authenticated: false
  },
  {
    name: 'Help',
    path: baseLinks.help,
    external: true,
    icon: 'icon-question',
    translate: 'global.nav.HELP',
    authenticated: false
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
  [SIDEBAR_PANE.syncProjectRepo]: 'Sync Repo',
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
  [SIDEBAR_PANE.runDeployedCodeBlock]: 'Code Runner',
  [SIDEBAR_PANE.sharedFiles]: 'Shared Files (Files Saved to Multiple Code Blocks)',
  [SIDEBAR_PANE.editSharedFile]: 'Edit Shared File',
  [SIDEBAR_PANE.editSharedFileLinks]: 'Edit Shared File Link(s)',
  [SIDEBAR_PANE.addingSharedFileLink]: 'Link Shared File to Code Block',
  [SIDEBAR_PANE.codeBlockSharedFiles]: 'Code Block Shared File(s)',
  [SIDEBAR_PANE.viewSharedFile]: 'Shared File Contents',
  [SIDEBAR_PANE.viewReadme]: 'Refinery Project README',
  [SIDEBAR_PANE.editReadme]: 'Project README'
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

export function getSidebarMenuItems(isRepoPresent: boolean): NavbarItem[] {
  const saveSidebarItem = isRepoPresent
    ? makeSidebarMenuItem(SIDEBAR_PANE.syncProjectRepo, 'fab fa-github', 'sidebar.nav.IMPORT_PROJECT', 'success')
    : makeSidebarMenuItem(SIDEBAR_PANE.saveProject, 'far fa-save', 'sidebar.nav.SAVE_PROJECT', 'success');

  return [
    makeSidebarMenuItem(SIDEBAR_PANE.addBlock, 'icon-plus', 'sidebar.nav.ADD_BLOCK', 'outline-primary'),
    makeSidebarMenuItem(
      SIDEBAR_PANE.addTransition,
      'icon-cursor-move',
      'sidebar.nav.ADD_TRANSITION',
      'outline-primary'
    ),
    makeSidebarMenuItem(SIDEBAR_PANE.runEditorCodeBlock, 'icon-control-play', 'RUN_CODE_BLOCK', 'outline-success'),
    makeSidebarMenuItem(SIDEBAR_PANE.sharedFiles, 'icon-docs', 'RUN_CODE_BLOCK', 'outline-primary'),
    // makeSidebarMenuItem(SIDEBAR_PANE.allBlocks, 'icon-grid', 'sidebar.nav.ALL_BLOCKS', 'outline-info'),
    // makeSidebarMenuItem(SIDEBAR_PANE.allVersions, 'icon-chart', 'sidebar.nav.ALL_VERSIONS', 'outline-info'),
    makeSidebarMenuItem(SIDEBAR_PANE.editReadme, 'fab fa-readme', 'sidebar.nav.VIEW_README', 'outline-primary'),
    makeSidebarMenuItem(
      SIDEBAR_PANE.exportProject,
      'icon-cloud-download',
      'sidebar.nav.EXPORT_PROJECT',
      'outline-info'
    ),
    saveSidebarItem,
    makeSidebarMenuItem(SIDEBAR_PANE.deployProject, 'icon-cloud-upload', 'sidebar.nav.DEPLOY_PROJECT', 'primary')
  ];
}

export const DeploymentSidebarMenuItems: NavbarItem[] = [
  // TODO: Finish this functionality
  // makeSidebarMenuItem(SIDEBAR_PANE.viewApiEndpoints, 'icon-list', 'sidebar.nav.VIEW_API_ENDPOINTS', 'outline-info'),
  makeSidebarMenuItem(SIDEBAR_PANE.viewExecutions, 'icon-organization', 'sidebar.nav.VIEW_EXECUTIONS', 'outline-info'),
  makeSidebarMenuItem(SIDEBAR_PANE.runDeployedCodeBlock, 'icon-control-play', 'RUN_CODE_BLOCK', 'outline-success'),
  makeSidebarMenuItem(SIDEBAR_PANE.destroyDeploy, 'icon-ban', 'sidebar.nav.DESTROY_DEPLOY', 'danger')
];
