import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import OpenedProjectGraphContainer from '@/containers/OpenedProjectGraphContainer';
import { Getter, namespace } from 'vuex-class';
import SidebarNav from '@/components/SidebarNav';
import { paneTypeToNameLookup, SidebarMenuItems } from '@/menu';
import ProjectEditorLeftPaneContainer from '@/containers/ProjectEditorLeftPaneContainer';
import { DeployProjectResult, PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import EditorPaneWrapper from '@/components/EditorPaneWrapper';
import { paneToContainerMapping } from '@/constants/project-editor-pane-constants';
import { UserInterfaceState } from '@/store/store-types';

const project = namespace('project');
const editBlock = namespace('project/editBlockPane');
const editTransition = namespace('project/editTransitionPane');

@Component
export default class OpenedProjectOverview extends Vue {
  @project.State isLoadingProject!: boolean;
  @project.State isSavingProject!: boolean;
  @project.State isInDemoMode!: boolean;
  @project.State activeLeftSidebarPane!: SIDEBAR_PANE | null;
  @project.State activeRightSidebarPane!: SIDEBAR_PANE | null;

  @Getter settings!: UserInterfaceState;

  @project.Getter canSaveProject!: boolean;
  @project.Getter canDeployProject!: boolean;
  @project.Getter transitionAddButtonEnabled!: boolean;
  @project.Getter hasCodeBlockSelected!: boolean;
  @project.Getter isProjectRepoSet!: boolean;

  @project.Action openLeftSidebarPane!: (paneType: SIDEBAR_PANE) => {};

  @project.Action closePane!: (p: PANE_POSITION) => void;

  @editBlock.Action tryToCloseBlock!: () => void;
  @editTransition.Action('tryToClose') tryToCloseTransition!: () => void;

  public handleItemClicked(pane: SIDEBAR_PANE) {
    // Handle us clicking the same pane twice.
    if (this.activeLeftSidebarPane === pane) {
      this.closePane(PANE_POSITION.left);
      return;
    }

    this.openLeftSidebarPane(pane);
  }

  renderSaveButtonContent() {
    if (!this.isSavingProject) {
      return null;
    }

    return (
      <div class="display--flex flex-direction--column align-items-center">
        <b-spinner small={true} type="grow" />
        <span>Saving...</span>
      </div>
    );
  }

  renderPaneOverlay(position: PANE_POSITION, paneType: SIDEBAR_PANE | null) {
    if (!paneType) {
      return null;
    }

    const paneProps: { paneTitle: string; closePane: () => void; tryToCloseBlock?: () => void } = {
      paneTitle: paneTypeToNameLookup[paneType],
      closePane: () => this.closePane(position)
    };

    if (paneType === SIDEBAR_PANE.editBlock) {
      paneProps.tryToCloseBlock = () => this.tryToCloseBlock();
    }

    if (paneType === SIDEBAR_PANE.editTransition) {
      paneProps.tryToCloseBlock = () => this.tryToCloseTransition();
    }

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
    const containerClasses = {
      'opened-project-overview': true,
      'display--flex': true,
      'flex-grow--1': true
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
      onNavItemClicked: this.handleItemClicked,
      paneTypeToActiveCheckFunction: {
        [SIDEBAR_PANE.addBlock]: () =>
          this.activeLeftSidebarPane === SIDEBAR_PANE.addBlock ||
          this.activeLeftSidebarPane === SIDEBAR_PANE.addSavedBlock
      },
      paneTypeToEnabledCheckFunction: {
        [SIDEBAR_PANE.addTransition]: () => this.transitionAddButtonEnabled,
        [SIDEBAR_PANE.saveProject]: () => this.isInDemoMode || this.canSaveProject,
        [SIDEBAR_PANE.importProjectRepo]: () => this.isProjectRepoSet,
        [SIDEBAR_PANE.deployProject]: () => this.canDeployProject,
        [SIDEBAR_PANE.runEditorCodeBlock]: () => this.hasCodeBlockSelected
      },
      paneTypeToCustomContentFunction: {
        [SIDEBAR_PANE.saveProject]: () => this.renderSaveButtonContent()
      }
    };

    return (
      <div class={containerClasses}>
        <div class="project-sidebar-container">
          <SidebarNav props={sidebarNavProps} />
        </div>

        <ProjectEditorLeftPaneContainer />

        <div class="project-sidebar-container__filler" />

        {this.renderPaneOverlay(PANE_POSITION.right, this.activeRightSidebarPane)}

        <OpenedProjectGraphContainer />
      </div>
    );
  }
}
