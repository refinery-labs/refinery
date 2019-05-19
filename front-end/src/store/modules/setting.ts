/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import {RootState, UserInterfaceSettings, UserInterfaceState} from '@/store/store-types';

const moduleState: UserInterfaceState = {
  /* Layout fixed. Scroll content only */
  [UserInterfaceSettings.isFixed]: true,
  /* Sidebar collapsed */
  [UserInterfaceSettings.isCollapsed]: false,
  /* Boxed layout */
  [UserInterfaceSettings.isBoxed]: false,
  /* Floating sidebar */
  [UserInterfaceSettings.isFloat]: false,
  /* Sidebar show menu on hover only */
  [UserInterfaceSettings.asideHover]: false,
  /* Show sidebar scrollbar (dont' hide it) */
  [UserInterfaceSettings.asideScrollbar]: false,
  /* Sidebar collapsed with big icons and text */
  [UserInterfaceSettings.isCollapsedText]: false,
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
  [UserInterfaceSettings.hiddenFooter]: false
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
    toggleSetting(state, name: UserInterfaceSettings) {
      if (name in state)
        state[name] = !state[name];
    },
    /**
     * Change a setting value
     * payload.name: name of the setting prop to change
     * payload.value: new value to apply
     */
    changeSetting(state, {name, value}: { name: UserInterfaceSettings, value: boolean }) {
      if (name in state)
        state[name] = value;
    }
  },
  actions: {}
};

export default SettingModule;