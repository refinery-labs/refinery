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
  private paneTypeToActiveCheckFunction!: {
    [index: string]: () => boolean;
  };
  @Prop({ default: () => ({}) })
  private paneTypeToEnabledCheckFunction!: {
    [index: string]: () => boolean;
  };
  @Prop({ default: () => ({}) })
  private paneTypeToCustomContentFunction!: {
    [index: string]: () => [];
  };

  public getIfButtonActive(paneType: string) {
    if (this.paneTypeToActiveCheckFunction[paneType]) {
      return this.paneTypeToActiveCheckFunction[paneType]();
    }

    return paneType === this.activeLeftSidebarPane;
  }

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
    const isActive = this.getIfButtonActive(navItem.editorPane);

    const enabled = this.getIfButtonEnabled(navItem.editorPane);

    const divClasses = {
      'content-sidebar__item': true
    };

    const buttonClasses = {
      'width--100percent': true,
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
      return (
        <div class={divClasses}>
          <b-button class={buttonClasses} props={buttonProps} on={buttonOnClicks}>
            {customContent}
          </b-button>
        </div>
      );
    }

    return (
      <div class={divClasses}>
        <b-button class={buttonClasses} props={buttonProps} on={buttonOnClicks}>
          <em class={navItem.icon} />
          <span>
            {splitContent[0]}
            <br />
            {splitContent[1] && splitContent[1]}
          </span>
        </b-button>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    return <div class="content-sidebar display--flex">{this.navItems.map(item => this.renderNavItem(item))}</div>;
  }
}
