import Vue from 'vue';
import { Component, Watch } from 'vue-property-decorator';
import { Route } from 'vue-router';
import { UserInterfaceSettings, UserInterfaceState } from '@/store/store-types';
import { Action, Getter, Mutation } from 'vuex-class';
import { MenuItem, MenuItemList } from '@/types/layout-types';
import { GlobalNavMenuItems } from '@/menu';

@Component
export default class GlobalNavSidebar extends Vue {
  private collapse!: { [key: string]: boolean };

  @Mutation toggleSettingOn!: (name: UserInterfaceSettings) => {};
  @Mutation toggleSettingOff!: (name: UserInterfaceSettings) => {};
  @Action closeGlobalNav!: () => {};

  @Watch('$route', { deep: true })
  private elementsModified(val: Route, oldVal: Route) {
    this.toggleGlobalNavOff();
  }

  data() {
    return {
      collapse: this.buildCollapseList()
    };
  }

  buildCollapseList() {
    // I hate this code, it's pulled from a theme we used... I'm sorry.
    /** prepare initial state of collapse menus. Doesnt allow same route names */
    let collapse: { [key: string]: boolean } = {};
    GlobalNavMenuItems.filter(
      (menuItem: MenuItem) => !menuItem.heading
    ).forEach((menuItem: MenuItem) => {
      const { name, path, submenu } = menuItem;

      if (!name) {
        return;
      }

      if (submenu) {
        if (submenu.length === 0) {
          return;
        }

        const paths = submenu
          .map(({ path }) => path)
          .filter(v => v) as string[];

        collapse[name] = this.isRouteActive(paths);
        return;
      }

      if (!path) {
        return;
      }

      collapse[name] = this.isRouteActive(path);
    });
    return collapse;
  }

  public toggleGlobalNavOff() {
    // this.toggleSettingOff(UserInterfaceSettings.isGlobalNavCollapsed);
    this.closeGlobalNav();
  }

  isRouteActive(paths: string | string[]) {
    paths = Array.isArray(paths) ? paths : [paths];
    return paths.some(p => {
      const currentPath = this.$route.path;

      // Special case for the home route
      if (p.length === 1) {
        return currentPath.length === 1;
      }

      return currentPath.indexOf(p) > -1;
    });
  }

  routeActiveClass(paths: string[]) {
    return { active: this.isRouteActive(paths) };
  }

  getSubRoutes(item: MenuItem) {
    if (!item || !item.submenu) {
      return null;
    }

    return item.submenu.map(({ path }) => path).filter(p => p) as string[];
  }

  toggleItemCollapse(collapseName: string) {
    for (let c in this.collapse) {
      if (this.collapse[c] === true && c !== collapseName)
        this.collapse[c] = false;
    }
    this.collapse[collapseName] = !this.collapse[collapseName];
  }

  renderSubmenuItem(item: MenuItem) {
    const itemColor = (item.label && item.label.color) || 'default';

    const spanToRender = item.label && (
      <span class={'float-right badge badge-' + itemColor}>
        {(item.label && item.label.value) || 'Unknown Subitem'}
      </span>
    );

    return (
      <router-link tag="li" to={item.path} active-class="active">
        <a title={item.name}>
          {spanToRender}
          <span>{item.name}</span>
        </a>
      </router-link>
    );
  }

  renderNavItem(item: MenuItem) {
    if (!item) {
      return null;
    }

    // Section header
    if (item.heading) {
      return (
        <li class="nav-heading">
          <span>{item.heading || 'STUBBED'}</span>
        </li>
      );
    }

    // Plain menu item
    if (!item.heading && !item.submenu) {
      return (
        <router-link
          to={item.path}
          active-class="active"
          tag="li"
          exact={item.path && item.path.length === 1}
        >
          <a title={item.name}>
            <span
              class={`float-right badge badge-${(item.label &&
                item.label.color) ||
                'default'}`}
            >
              {item.label}
            </span>
            <em class={item.icon} />
            <span>{item.name}</span>
          </a>
        </router-link>
      );
    }

    // Menu item with sub-menu
    if (!item.heading && item.submenu && item.name) {
      const subRoutes = this.getSubRoutes(item);

      if (!subRoutes) {
        return;
      }

      return (
        <li class={this.routeActiveClass(subRoutes)}>
          <a
            title={item.name}
            on={{ click: this.toggleItemCollapse.bind(this, item.name) }}
          >
            <span
              class={
                'float-right badge badge-' +
                ((item.label && item.label.color) || 'default')
              }
            >
              {(item.label && item.label.value) || 'Unknown Label'}
            </span>
            <em class={item.icon} />
            <span>{item.name}</span>
          </a>
          <b-collapse
            tag="ul"
            class="sidebar-nav sidebar-subnav"
            id="item.name"
            visible={this.collapse[item.name]}
          >
            <li bar={true} class="sidebar-subnav-header" />
            <div class="sidebar-subnav-header" />
            {item.submenu.map(submenu => this.renderSubmenuItem(submenu))}
          </b-collapse>
        </li>
      );
    }

    // You goofed, boyo!
    return null;
  }

  render() {
    return (
      <aside class="global-nav-container">
        {/*TODO: This needs to register clicks to allow escaping*/}
        <div
          class="global-nav-container-backdrop position--fixed display--block"
          on={{ click: this.toggleGlobalNavOff }}
        />
        <aside class="global-nav-container-inner position--fixed sidebar--left overflow-hidden">
          <nav class="sidebar">
            <ul class="sidebar-nav">
              {GlobalNavMenuItems.map((menuItem: MenuItem) =>
                this.renderNavItem(menuItem)
              )}
            </ul>
          </nav>
        </aside>
      </aside>
    );
  }
}
