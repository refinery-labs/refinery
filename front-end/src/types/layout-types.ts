export type MenuItemLabel = {
  value: number|string,
  color: string
};

export type MenuItem = {
  name?: string,
  icon?: string,
  translate?: string,
  label?: MenuItemLabel,
  path?: string,
  submenu?: MenuItem[],
  heading?: string
};

export type MenuItemList = MenuItem[];
