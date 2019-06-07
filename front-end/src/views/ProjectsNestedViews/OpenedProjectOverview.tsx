import Vue, { CreateElement, VNode } from "vue";
import Component from "vue-class-component";
import Offsidebar from "@/components/Layout/Offsidebar.vue";
import OpenedProjectGraphContainer from "@/containers/OpenedProjectGraphContainer";
import { Watch } from "vue-property-decorator";
import { Route } from "vue-router";
import { GetSavedProjectRequest } from "@/types/api-types";
import { namespace } from "vuex-class";
import SidebarNav from "@/components/SidebarNav";
import { paneTypeToNameLookup, SidebarMenuItems } from "@/menu";
import ProjectEditorLeftPaneContainer from "@/containers/ProjectEditorLeftPaneContainer";
import { PANE_POSITION, SIDEBAR_PANE } from "@/types/project-editor-types";
import EditorPaneWrapper from "@/components/EditorPaneWrapper";
import { paneToContainerMapping } from "@/constants/project-editor-constants";

const project = namespace("project");

@Component
export default class OpenedProjectOverview extends Vue {
  @project.State isLoadingProject!: boolean;
  @project.State activeLeftSidebarPane!: SIDEBAR_PANE | null;
  @project.State activeRightSidebarPane!: SIDEBAR_PANE | null;

  @project.Getter canSaveProject!: boolean;
  @project.Getter transitionAddButtonEnabled!: boolean;

  @project.Action openProject!: (projectId: GetSavedProjectRequest) => {};
  @project.Action openLeftSidebarPane!: (paneType: SIDEBAR_PANE) => {};

  @project.Action closePane!: (p: PANE_POSITION) => void;

  @Watch("$route", { immediate: true })
  private routeChanged(val: Route, oldVal: Route) {
    // Project is already opened
    if (
      val &&
      oldVal &&
      val.params.projectId &&
      val.params.projectId === oldVal.params.projectId
    ) {
      return;
    }

    this.openProject({ project_id: val.params.projectId });
  }

  renderLeftPaneOverlay() {
    return (
      <div class="project-pane-overlay-container project-pane-overlay-container--left">
        <ProjectEditorLeftPaneContainer />
      </div>
    );
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
      <div
        class={`project-pane-overlay-container project-pane-overlay-container--${position}`}
      >
        <EditorPaneWrapper props={paneProps}>{instance}</EditorPaneWrapper>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    // TODO: Add validation of the ID structure
    if (!this.$route.params.projectId) {
      return <h2>Please open a project first</h2>;
    }

    const containerClasses = {
      "opened-project-overview": true,
      "display--flex": true,
      "flex-grow--1": true
    };

    // Show a nice loading animation
    if (this.isLoadingProject) {
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
      navItems: SidebarMenuItems,
      activeLeftSidebarPane: this.activeLeftSidebarPane,
      onNavItemClicked: this.openLeftSidebarPane,
      leftSidebarPaneTypeToEnabledCheckFunction: {
        [SIDEBAR_PANE.addTransition]: () => this.transitionAddButtonEnabled,
        [SIDEBAR_PANE.saveProject]: () => this.canSaveProject
      }
    };

    return (
      <div class={containerClasses}>
        <div class="project-sidebar-container">
          <SidebarNav props={sidebarNavProps} />
        </div>

        {this.renderLeftPaneOverlay()}

        <OpenedProjectGraphContainer />

        {this.renderPaneOverlay(
          PANE_POSITION.right,
          this.activeRightSidebarPane
        )}
      </div>
    );
  }
}
