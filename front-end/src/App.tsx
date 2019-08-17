import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import SidebarNav from '@/components/SidebarNav';
import TopNavbar from '@/components/TopNavbar';
import { UserInterfaceSettings, UserInterfaceState } from '@/store/store-types';
import { Action, Getter, namespace } from 'vuex-class';
import ToastContainer from '@/containers/ToastContainer';
import IntercomWrapper from './lib/IntercomWrapper';

const user = namespace('user');

@Component({
  components: {
    SidebarNav,
    TopNavbar
  }
})
export default class App extends Vue {
  @user.State name!: string | null;
  @user.State email!: string | null;
  @user.State intercomUserHmac!: string | null;

  @Getter settings!: UserInterfaceState;
  @Action setIsAWSConsoleCredentialModalVisibleValue!: (visible: boolean) => {};

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
        {this.renderAWSConsoleModal()}
        <ToastContainer />
        <IntercomWrapper
          props={{
            name: this.name,
            email: this.email,
            intercomUserHmac: this.intercomUserHmac
          }}
        />
      </div>
    );
  }
}
