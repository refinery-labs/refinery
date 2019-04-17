import {CreateElement, VNode} from 'vue';
import {Component, Prop, Vue} from 'vue-property-decorator';
import '@/styles/app.scss';

export declare type NavItem = {link: string, text: string, color: string};

@Component
export default class SidebarNav extends Vue {
  @Prop({default: []})
  private navItems!: NavItem[];
  
  public renderNavItem(navItem: NavItem) {
    return (
      <router-link to={navItem.link}
                   class={"sidebar-nav__item display--flex sidebar-nav__item--" + navItem.color}>
        <h3 class="center--all">
          {navItem.text}
        </h3>
      </router-link>
    );
  }
  
  public render(h: CreateElement): VNode {
    const navItems: NavItem[] = this.$props.navItems;
    return (
      <div class="sidebar-nav display--flex flex-direction--column">
        {navItems.map((item) => this.renderNavItem(item))}
      </div>
    );
  }
}
