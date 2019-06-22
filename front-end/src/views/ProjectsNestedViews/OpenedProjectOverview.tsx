import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import OpenedProjectGraphContainer from '@/containers/OpenedProjectGraphContainer';
import { Watch } from 'vue-property-decorator';
import { Route } from 'vue-router';
import { GetSavedProjectRequest } from '@/types/api-types';
import { Action, Getter, namespace } from 'vuex-class';
import SidebarNav from '@/components/SidebarNav';
import { paneTypeToNameLookup, SidebarMenuItems } from '@/menu';
import ProjectEditorLeftPaneContainer from '@/containers/ProjectEditorLeftPaneContainer';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import EditorPaneWrapper from '@/components/EditorPaneWrapper';
import { paneToContainerMapping } from '@/constants/project-editor-constants';
import { UserInterfaceSettings, UserInterfaceState } from '@/store/store-types';
import { SettingsMutators } from '@/constants/store-constants';

const project = namespace('project');
const editBlock = namespace('project/editBlockPane');

@Component
export default class OpenedProjectOverview extends Vue {
  @project.State isLoadingProject!: boolean;
  @project.State isSavingProject!: boolean;
  @project.State activeLeftSidebarPane!: SIDEBAR_PANE | null;
  @project.State activeRightSidebarPane!: SIDEBAR_PANE | null;

  @Getter settings!: UserInterfaceState;
  @Action setIsAWSConsoleCredentialModalVisibleValue!: (visible: boolean) => {};

  @project.Getter canSaveProject!: boolean;
  @project.Getter canDeployProject!: boolean;
  @project.Getter transitionAddButtonEnabled!: boolean;
  @project.Getter hasCodeBlockSelected!: boolean;

  @project.Action openLeftSidebarPane!: (paneType: SIDEBAR_PANE) => {};

  @project.Action closePane!: (p: PANE_POSITION) => void;

  @editBlock.Action tryToCloseBlock!: () => void;

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
      closePane: () => this.closePane(position),
      tryToCloseBlock: () => this.tryToCloseBlock()
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

  /*
    The actual AWS Console credentials form display
   */
  renderAWSConsoleLoginInformation() {
    const buttonOnClicks = {
      click: () => {
        if (this.settings.AWSConsoleCredentials === null) {
          return;
        }
        window.open(this.settings.AWSConsoleCredentials.signin_url, '_blank');
      }
    };
    return (
      <div>
        <div class="text-align--center">
          To access your Refinery-Managed AWS Account, click the button below and enter the provided credentials.
          <br />
          <hr />
          <b-button on={buttonOnClicks} variant="primary">
            Open AWS Console Login Page <span class="fas fa-external-link-alt" />
          </b-button>
        </div>
        <hr />
        <b-form-group
          label="IAM user name:"
          label-for="console-login-username"
          description="Enter this into the 'IAM user name' field of the AWS login page."
        >
          <b-form-input
            id="console-login-username"
            type="text"
            required
            placeholder="Please wait, loading IAM credentials..."
            value={this.settings.AWSConsoleCredentials ? this.settings.AWSConsoleCredentials.username : ''}
          />
        </b-form-group>
        <b-form-group
          label="Password:"
          label-for="console-login-password"
          description="Enter this into the 'Password' field of the AWS login page."
        >
          <b-form-input
            id="console-login-password"
            type="text"
            required
            placeholder="Please wait, loading IAM credentials..."
            value={this.settings.AWSConsoleCredentials ? this.settings.AWSConsoleCredentials.password : ''}
          />
        </b-form-group>
        <b-form-group
          label="AWS Console Login URL:"
          label-for="console-login-url"
          description="Optional field useful for if you need to copy the URL to another window (e.g. incognito)."
        >
          <b-form-input
            id="console-login-url"
            type="text"
            required
            placeholder="Please wait, loading IAM credentials..."
            value={this.settings.AWSConsoleCredentials ? this.settings.AWSConsoleCredentials.signin_url : ''}
          />
        </b-form-group>
      </div>
    );
  }

  /*
    Displays a modal with AWS console credentials to log in.
  */
  renderAWSConsoleModal() {
    if (!this.settings.isAWSConsoleCredentialModalVisible) {
      return <div />;
    }
    const modalOnHandlers = {
      hidden: () => this.setIsAWSConsoleCredentialModalVisibleValue(false),
      ok: () => this.setIsAWSConsoleCredentialModalVisibleValue(false)
    };
    return (
      <b-modal
        on={modalOnHandlers}
        ok-variant="danger"
        footer-class="p-2"
        ref="console-modal"
        hide-footer
        title="Refinery Managed AWS Console Credentials"
        visible={this.settings.isAWSConsoleCredentialModalVisible}
      >
        {this.renderAWSConsoleLoginInformation()}
      </b-modal>
    );
  }

  public render(h: CreateElement): VNode {
    // TODO: Add validation of the ID structure
    if (!this.$route.params.projectId) {
      return <h2>Please open a project first</h2>;
    }

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
      paneTypeToEnabledCheckFunction: {
        [SIDEBAR_PANE.addTransition]: () => this.transitionAddButtonEnabled,
        [SIDEBAR_PANE.saveProject]: () => this.canSaveProject,
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

        {this.renderAWSConsoleModal()}

        {this.renderLeftPaneOverlay()}

        <OpenedProjectGraphContainer />

        {this.renderPaneOverlay(PANE_POSITION.right, this.activeRightSidebarPane)}
      </div>
    );
  }
}
