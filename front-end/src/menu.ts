import {baseLinks} from '@/constants/router-constants';
import {MenuItemList, NavbarItem} from '@/types/layout-types';
import {LEFT_SIDEBAR_PANE} from '@/types/project-editor-types';

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
  },
  {
    name: 'All Projects',
    path: baseLinks.projects,
    icon: 'icon-chemistry',
    translate: 'global.nav.PROJECTS',
  },
  {
    name: 'Marketplace',
    path: baseLinks.marketplace,
    icon: 'icon-basket',
    translate: 'global.nav.MARKETPLACE',
  },
  {
    name: 'Settings',
    path: baseLinks.settings,
    icon: 'icon-settings',
    translate: 'global.nav.SETTINGS',
  },
  {
    name: 'About',
    path: baseLinks.about,
    icon: 'icon-info',
    translate: 'global.nav.ABOUT',
  },
  {
    name: 'Billing',
    path: baseLinks.billing,
    icon: 'icon-wallet',
    translate: 'global.nav.BILLINGx',
  },
  {
    name: 'Help',
    path: baseLinks.help,
    icon: 'icon-question',
    translate: 'global.nav.HELP',
  }
];

export const WorkflowEditorMenuItems: MenuItemList = [
  {
    heading: 'Main Navigation',
    translate: 'sidebar.heading.HEADER'
  },
  {
    name: 'Blocks',
    icon: 'icon-plus',
    translate: 'sidebar.nav.BLOCKS'
  },
  {
    name: 'Entrypoints',
    icon: 'icon-layers',
    translate: 'sidebar.nav.ENTRYPOINTS'
  },
  // {
  //   name: 'Widgets',
  //   icon: 'icon-grid',
  //   path: '/widgets',
  //   label: { value: 30, color: 'success' },
  //   translate: 'sidebar.nav.WIDGETS'
  // },
  // {
  //   name: 'Layout',
  //   icon: 'icon-layers',
  //   submenu: [{
  //     name: 'Horizontal',
  //     path: '/dashboard'
  //   }
  //   ]
  // },
];

export type EditorPaneTypeToName = {
  [key in LEFT_SIDEBAR_PANE]: string;
}

export const paneTypeToNameLookup: EditorPaneTypeToName = {
  [LEFT_SIDEBAR_PANE.addBlock]: 'Add Block',
  [LEFT_SIDEBAR_PANE.addTransition]: 'Add Transition',
  [LEFT_SIDEBAR_PANE.allBlocks]: 'All Blocks',
  [LEFT_SIDEBAR_PANE.allVersions]: 'All Versions',
  [LEFT_SIDEBAR_PANE.saveProject]: 'Save Project',
  [LEFT_SIDEBAR_PANE.deployProject]: 'Deploy Project'
};

export const paneTypeToWindowNameLookup: EditorPaneTypeToName = {
  ...paneTypeToNameLookup,
  [LEFT_SIDEBAR_PANE.addBlock]: `Click to ${paneTypeToNameLookup[LEFT_SIDEBAR_PANE.addBlock]}`
};

// TODO: Make a small helper to generate these instead of copy-pasting
export const SidebarMenuItems: NavbarItem[] = [
  {
    name: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.addBlock],
    icon: 'icon-plus',
    translate: 'sidebar.nav.ADD_BLOCK',
    label: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.addBlock],
    buttonVariant: 'outline-primary',
    editorPane: LEFT_SIDEBAR_PANE.addBlock
  },
  {
    name: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.addTransition],
    icon: 'icon-cursor-move',
    translate: 'sidebar.nav.ADD_TRANSITION',
    label: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.addTransition],
    buttonVariant: 'outline-primary',
    editorPane: LEFT_SIDEBAR_PANE.addTransition
  },
  {
    name: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.allBlocks],
    icon: 'icon-grid',
    translate: 'sidebar.nav.ALL_BLOCKS',
    label: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.allBlocks],
    buttonVariant: 'outline-info',
    editorPane: LEFT_SIDEBAR_PANE.allBlocks
  },
  {
    name: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.allVersions],
    icon: 'icon-chart',
    translate: 'sidebar.nav.ALL_VERSIONS',
    label: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.allVersions],
    buttonVariant: 'outline-info',
    editorPane: LEFT_SIDEBAR_PANE.allVersions
  },
  {
    name: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.saveProject],
    icon: 'icon-check',
    translate: 'sidebar.nav.SAVE_PROJECT',
    label: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.saveProject],
    buttonVariant: 'success',
    editorPane: LEFT_SIDEBAR_PANE.saveProject
  },
  {
    name: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.deployProject],
    icon: 'icon-cloud-upload',
    translate: 'sidebar.nav.DEPLOY_PROJECT',
    label: paneTypeToNameLookup[LEFT_SIDEBAR_PANE.deployProject],
    buttonVariant: 'primary',
    editorPane: LEFT_SIDEBAR_PANE.deployProject
  }
];
