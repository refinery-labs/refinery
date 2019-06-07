import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { NavbarItem } from '@/types/layout-types';
import { SIDEBAR_PANE } from '@/types/project-editor-types';

@Component
export default class SidebarNav extends Vue {
  @Prop({ required: true }) private navItems!: NavbarItem[];
  @Prop({ required: true }) private onNavItemClicked!: (s: SIDEBAR_PANE) => {};
  @Prop({ required: true }) private activeLeftSidebarPane!: SIDEBAR_PANE | null;
  @Prop({ default: () => ({}) })
  private leftSidebarPaneTypeToEnabledCheckFunction!: {
    [index: string]: () => boolean;
  };

  public getIfButtonEnabled(paneType: string) {
    if (this.leftSidebarPaneTypeToEnabledCheckFunction[paneType]) {
      return this.leftSidebarPaneTypeToEnabledCheckFunction[paneType]();
    }

    return true;
  }

  public renderNavItem(navItem: NavbarItem) {
    const isActive = navItem.editorPane === this.activeLeftSidebarPane;

    const enabled = this.getIfButtonEnabled(navItem.editorPane);

    const buttonClasses = {
      'content-sidebar__item': true,
      active: isActive,
      focus: isActive
    };

    const splitContent = navItem.name.split(' ');

    return (
      <b-button
        class={buttonClasses}
        variant={navItem.buttonVariant}
        disabled={!enabled}
        on={{ click: () => this.onNavItemClicked(navItem.editorPane) }}
      >
        <em class={navItem.icon} />
        <br />
        <span>
          {splitContent[0]}
          <br />
          {splitContent[1] && splitContent[1]}
        </span>
      </b-button>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <ul class="content-sidebar display--flex flex-direction--column padding-left--none">
        {this.navItems.map(item => this.renderNavItem(item))}
      </ul>
    );
  }
}
