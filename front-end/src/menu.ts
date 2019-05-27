import {baseLinks} from '@/constants/router-constants';
import {MenuItemList} from '@/types/layout-types';

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

export const SidebarMenuItems: MenuItemList = [
  {
    name: 'Blocks',
    icon: 'icon-grid',
    path: '/asdf',
    translate: 'sidebar.nav.BLOCKS'
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
