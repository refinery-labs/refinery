/**
 * Setting store to control layout behavior
 */
import { Module } from 'vuex';
import { RootState, UserInterfaceSettings, UserInterfaceState } from '@/store/store-types';
import { SettingsActions, SettingsMutators } from '@/constants/store-constants';
import { ConsoleCredentials } from '@/types/api-types';
import { getConsoleCredentials } from '@/store/fetchers/api-helpers';

const moduleState: UserInterfaceState = {
  /* Layout fixed. Scroll content only */
  [UserInterfaceSettings.isFixed]: true,
  /* Global Nav collapsed */
  [UserInterfaceSettings.isGlobalNavCollapsed]: false,
  /* Global Nav closing, fires when nav is closed */
  [UserInterfaceSettings.isGlobalNavClosing]: false,
  /* Sidebar collapsed */
  [UserInterfaceSettings.isSidebarCollapsed]: false,
  /* Boxed layout */
  [UserInterfaceSettings.isBoxed]: false,
  /* Floating sidebar */
  [UserInterfaceSettings.isFloat]: false,
  /* Sidebar show menu on hover only */
  [UserInterfaceSettings.asideHover]: false,
  /* Show sidebar scrollbar (dont' hide it) */
  [UserInterfaceSettings.asideScrollbar]: false,
  /* Sidebar collapsed with big icons and text */
  [UserInterfaceSettings.isCollapsedText]: true,
  /* Toggle for the offsidebar */
  [UserInterfaceSettings.offsidebarOpen]: false,
  /* Toggle for the sidebar offcanvas (mobile) */
  [UserInterfaceSettings.asideToggled]: false,
  /* Toggle for the sidebar user block */
  [UserInterfaceSettings.showUserBlock]: false,
  /* Enables layout horizontal */
  [UserInterfaceSettings.horizontal]: false,
  /* Full size layout */
  [UserInterfaceSettings.useFullLayout]: false,
  /* Hide footer */
  [UserInterfaceSettings.hiddenFooter]: false,
  /* Boolean to display the AWS console credentials */
  [UserInterfaceSettings.isAWSConsoleCredentialModalVisible]: false,
  /* AWS console credentials */
  [UserInterfaceSettings.AWSConsoleCredentials]: null
};

const SettingModule: Module<UserInterfaceState, RootState> = {
  // This is difficult to use and Mutators don't seem to work in consumers?
  // namespaced: true,
  state: moduleState,
  getters: {
    settings: state => state
  },
  mutations: {
    /**
     * Toggle a setting value (only boolean)
     */
    [SettingsMutators.toggleSetting](state, name: UserInterfaceSettings) {
      if (name in state) state[name] = !state[name];
    },
    /**
     * Toggle a setting off
     */
    [SettingsMutators.toggleSettingOff](state, name: UserInterfaceSettings) {
      if (name in state) state[name] = false;
    },
    /**
     * Toggle a setting on
     */
    [SettingsMutators.toggleSettingOn](state, name: UserInterfaceSettings) {
      if (name in state) state[name] = true;
    },
    /**
     * Change a setting value
     * payload.name: name of the setting prop to change
     * payload.value: new value to apply
     */
    [SettingsMutators.changeSetting](state, { name, value }: { name: UserInterfaceSettings; value: boolean }) {
      if (name in state) state[name] = value;
    },
    /**
     * Toggle displaying the AWS Console Credentials modal
     */
    [SettingsMutators.setIsAWSConsoleCredentialModalVisible](state, visible: boolean) {
      state.isAWSConsoleCredentialModalVisible = visible;
    },
    /**
     * Store the AWS credentials for users to log into their AWS console
     */
    [SettingsMutators.setAWSConsoleCredentials](state, credentials: ConsoleCredentials) {
      state.AWSConsoleCredentials = credentials;
    }
  },
  actions: {
    setIsAWSConsoleCredentialModalVisibleValue(context, visible: boolean) {
      // If view modal is true we'll kick off loading the credentials as well.
      if (visible) {
        context.dispatch('getAWSConsoleCredentials');
      }

      context.commit(SettingsMutators.setIsAWSConsoleCredentialModalVisible, visible);
    },
    async getAWSConsoleCredentials(context) {
      const newConsoleCredentials = await getConsoleCredentials();
      context.commit(SettingsMutators.setAWSConsoleCredentials, newConsoleCredentials);
    },
    closeGlobalNav(context) {
      if (!context.state.isGlobalNavCollapsed) {
        return;
      }

      context.commit(SettingsMutators.toggleSettingOn, UserInterfaceSettings.isGlobalNavClosing);

      // We throw this timer in here to allow the CSS to do it's magic.
      // Sure, we could listen to the animation events and trigger this there... But we're lazy, okay?
      setTimeout(() => {
        context.commit(SettingsMutators.toggleSetting, UserInterfaceSettings.isGlobalNavCollapsed);
        context.commit(SettingsMutators.toggleSettingOff, UserInterfaceSettings.isGlobalNavClosing);
      }, 220);
    }
  }
};

export default SettingModule;
