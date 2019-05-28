import {CreateElement, VNode} from 'vue';
import {Component, Prop, Vue} from 'vue-property-decorator';
import {MenuItem, MenuItemList} from '@/types/layout-types';

@Component
export default class SidebarNav extends Vue {
  @Prop({default: () => []}) private navItems!: MenuItemList;
  
  public renderNavItem(navItem: MenuItem) {
    const labelColor = navItem.label && navItem.label.color || 'default';
    
    const liClasses = {
      // 'center--all': true,
      'content-sidebar__item': true,
      'display--flex': true,
      [`content-sidebar__item--${labelColor}`]: true
    };
    
    return (
      <li class={liClasses}>
        <router-link title={navItem.label} to={navItem.path}>
          <em class={navItem.icon} />
          <span>{navItem.name}</span>
        </router-link>
      </li>
    );
  }
  
  public render(h: CreateElement): VNode {
    const navItems: MenuItemList = this.$props.navItems;
    return (
      <ul class="content-sidebar display--flex flex-direction--column padding-left--none">
        {navItems.map((item) => this.renderNavItem(item))}
      </ul>
    );
  }
}
