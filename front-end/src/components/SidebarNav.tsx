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
  private paneTypeToEnabledCheckFunction!: {
    [index: string]: () => boolean;
  };
  @Prop({default: () => ({}) })
  private paneTypeToCustomContentFunction!: {
    [index: string]: () => []
  };

  public getIfButtonEnabled(paneType: string) {
    if (this.paneTypeToEnabledCheckFunction[paneType]) {
      return this.paneTypeToEnabledCheckFunction[paneType]();
    }

    return true;
  }

  public getCustomContentIfSpecified(paneType: string) {
    if (this.paneTypeToCustomContentFunction[paneType]) {
      return this.paneTypeToCustomContentFunction[paneType]();
    }

    return null;
  }

  public renderNavItem(navItem: NavbarItem) {
    const isActive = navItem.editorPane === this.activeLeftSidebarPane;

    const enabled = this.getIfButtonEnabled(navItem.editorPane);

    const buttonClasses = {
      'content-sidebar__item': true,
      active: isActive,
      focus: isActive
    };

    const buttonOnClicks = { click: () => this.onNavItemClicked(navItem.editorPane) };

    const splitContent = navItem.name.split(' ');

    const customContent = this.getCustomContentIfSpecified(navItem.editorPane);

    const buttonProps = {
      variant: navItem.buttonVariant,
      disabled: !enabled
    };

    if (customContent) {
      return <b-button class={buttonClasses} props={buttonProps} on={buttonOnClicks}>
        {customContent}
      </b-button>
    }

    return (
      <b-button class={buttonClasses} props={buttonProps} on={buttonOnClicks}>
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
