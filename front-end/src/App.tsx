import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import SidebarNav, {NavItem} from '@/components/SidebarNav';
import TopNavbar from '@/components/TopNavbar';
import {UserInterfaceSettings, UserInterfaceState} from '@/store/store-types';
import {Getter} from 'vuex-class';
import {Watch} from 'vue-property-decorator';

@Component({
  components: {
    SidebarNav,
    TopNavbar
  }
})
export default class App extends Vue {
  @Getter settings!: UserInterfaceState;
  
  public render(h: CreateElement): VNode {
    const activeClasses = {
      'layout-fixed': this.settings[UserInterfaceSettings.isFixed],
      'layout-boxed': this.settings[UserInterfaceSettings.isBoxed],
      'global-nav-collapsed': !this.settings[UserInterfaceSettings.isGlobalNavCollapsed],
      'global-nav-closing': this.settings[UserInterfaceSettings.isGlobalNavClosing],
      'global-nav-visible': this.settings[UserInterfaceSettings.isGlobalNavCollapsed],
      'aside-collapsed': this.settings[UserInterfaceSettings.isSidebarCollapsed],
      'aside-collapsed-text': this.settings[UserInterfaceSettings.isCollapsedText],
      'aside-float': this.settings[UserInterfaceSettings.isFloat],
      'aside-hover': this.settings[UserInterfaceSettings.asideHover],
      'offsidebar-open': this.settings[UserInterfaceSettings.offsidebarOpen],
      'aside-toggled': this.settings[UserInterfaceSettings.asideToggled],
      'layout-h': this.settings[UserInterfaceSettings.horizontal],
      'display--flex': true,
      'height--100percent': true
    };
    
    return (
      <div id="app" class={activeClasses}>
        <div class="flex-grow--3">
          <router-view />
        </div>
      </div>
    );
  }
}
