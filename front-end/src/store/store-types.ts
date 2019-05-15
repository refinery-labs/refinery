export interface RootState {
  setting: UserInterfaceState
}

export enum UserInterfaceSettings {
  isFixed = 'isFixed',
  isCollapsed = 'isCollapsed',
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
  /* Sidebar collapsed */
  [UserInterfaceSettings.isCollapsed]?: boolean,
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
