import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { Route } from 'vue-router';
import { namespace } from 'vuex-class';
import SidebarNav from '@/components/SidebarNav';
import { paneTypeToNameLookup, DeploymentSidebarMenuItems } from '@/menu';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import EditorPaneWrapper from '@/components/EditorPaneWrapper';
import { paneToContainerMapping } from '@/constants/project-editor-constants';
import DeploymentViewerGraphContainer from '@/containers/DeploymentViewerGraphContainer';
import store from '@/store/index';
import { DeploymentViewActions } from '@/constants/store-constants';
import { DeploymentExecutionsMutators } from '@/store/modules/panes/deployment-executions-pane';

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

  // This handles fetching the data for the UI upon route entry
  // Note: We don't block the call to next because that allows the user to "see" the UI first, including a loading animation.
  // Maybe that is a mistake... But it feels reasonable also. Could re-evaluate this in the future?
  public async beforeRouteEnter(to: Route, from: Route, next: () => void) {
    next();

    // TODO: Check if the state is still valid to allow caching + faster UX
    await store.dispatch(`deployment/${DeploymentViewActions.openDeployment}`, to.params.projectId);
  }

  public beforeRouteLeave(to: Route, from: Route, next: () => void) {
    // Don't continue execution fetching job after we leave
    store.commit(`deploymentExecutions/${DeploymentExecutionsMutators.setAutoRefreshJobNonce}`, null);
    next();
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
      return <h2>Please wait...</h2>;
    }

    const containerClasses = {
      'opened-project-overview': true,
      'display--flex': true,
      'flex-grow--1': true,
      whirl: false,
      standard: false
    };

    // Show a nice loading animation
    if (this.isLoadingDeployment) {
      containerClasses.whirl = true;
      containerClasses.standard = true;
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
