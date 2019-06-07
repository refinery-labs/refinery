import { SIDEBAR_PANE } from '@/types/project-editor-types';

export type MenuItemLabel = {
  value: number | string;
  color: string;
};

export type MenuItem = {
  name?: string;
  icon?: string;
  translate?: string;
  label?: MenuItemLabel;
  path?: string;
  submenu?: MenuItem[];
  heading?: string;
};

export interface NavbarItem {
  name: string;
  icon: string;
  label: string;
  translate: string;
  buttonVariant: string;
  editorPane: SIDEBAR_PANE;
}

export type MenuItemList = MenuItem[];
