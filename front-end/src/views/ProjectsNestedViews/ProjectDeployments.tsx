import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { Watch } from 'vue-property-decorator';
import { Route } from 'vue-router';
import { namespace } from 'vuex-class';
import SidebarNav from '@/components/SidebarNav';
import { paneTypeToNameLookup, DeploymentSidebarMenuItems } from '@/menu';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import EditorPaneWrapper from '@/components/EditorPaneWrapper';
import { paneToContainerMapping } from '@/constants/project-editor-constants';
import DeploymentViewerGraphContainer from '@/containers/DeploymentViewerGraphContainer';

const deployment = namespace('deployment');

@Component
export default class ProjectDeployments extends Vue {
  @deployment.State isLoadingDeployment!: boolean;
  @deployment.State activeLeftSidebarPane!: SIDEBAR_PANE | null;
  @deployment.State activeRightSidebarPane!: SIDEBAR_PANE | null;

  @deployment.Getter hasValidDeployment!: boolean;

  @deployment.Action openDeployment!: (projectId: string) => {};
  @deployment.Action openLeftSidebarPane!: (paneType: SIDEBAR_PANE) => {};

  @deployment.Action closePane!: (p: PANE_POSITION) => void;

  @Watch('$route', { immediate: true })
  private routeChanged(val: Route, oldVal: Route) {
    // Project is already opened
    if (val && oldVal) {
      const isProjectAlreadyOpen = val.params.projectId && val.params.projectId === oldVal.params.projectId;
      const isDeploymentAlreadyOpen = val.name === 'deployment' && oldVal.name === 'deployment';

      if (isProjectAlreadyOpen && isDeploymentAlreadyOpen) {
        return;
      }
    }

    this.openDeployment(val.params.projectId);
  }

  public handleItemClicked(pane: SIDEBAR_PANE) {
    // Handle us clicking the same pane twice.
    if (this.activeLeftSidebarPane === pane) {
      this.closePane(PANE_POSITION.left);
      return;
    }

    this.openLeftSidebarPane(pane);
  }

  renderPaneOverlay(position: PANE_POSITION, paneType: SIDEBAR_PANE | null) {
    if (!paneType) {
      return null;
    }

    const paneProps = {
      paneTitle: paneTypeToNameLookup[paneType],
      closePane: () => this.closePane(position)
    };

    const ActivePane = paneToContainerMapping[paneType];
    // @ts-ignore
    const instance = <ActivePane slot="pane" />;

    return (
      <div class={`project-pane-overlay-container project-pane-overlay-container--${position}`}>
        <EditorPaneWrapper props={paneProps}>{instance}</EditorPaneWrapper>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    // TODO: Add validation of the ID structure
    if (!this.$route.params.projectId) {
      return <h2>Please open a project a first</h2>;
    }

    if (!this.hasValidDeployment) {
      return (
        <h2>
          You must deploy this project before you can view a project's deployment. You may do this from the Overview
          pane.
        </h2>
      );
    }

    const containerClasses = {
      'opened-project-overview': true,
      'display--flex': true,
      'flex-grow--1': true
    };

    // Show a nice loading animation
    if (this.isLoadingDeployment) {
      return (
        <div
          class={{
            ...containerClasses,
            whirl: true,
            standard: true
          }}
        />
      );
    }

    const sidebarNavProps = {
      navItems: DeploymentSidebarMenuItems,
      activeLeftSidebarPane: this.activeLeftSidebarPane,
      onNavItemClicked: this.handleItemClicked,
      leftSidebarPaneTypeToEnabledCheckFunction: {}
    };

    return (
      <div class={containerClasses}>
        <div class="project-sidebar-container">
          <SidebarNav props={sidebarNavProps} />
        </div>

        {this.renderPaneOverlay(PANE_POSITION.left, this.activeLeftSidebarPane)}

        <DeploymentViewerGraphContainer />

        {this.renderPaneOverlay(PANE_POSITION.right, this.activeRightSidebarPane)}
      </div>
    );
  }
}
