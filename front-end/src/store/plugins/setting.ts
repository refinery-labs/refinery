// Helpers to change class attribute
import { RootState } from '@/store/store-types';
import { Store } from 'vuex';

function updateElementClass(el: Element | null, stat: boolean | undefined, name: string) {
  return el && el.classList[stat ? 'add' : 'remove'](name);
}
function updateBodyClass(stat: boolean | undefined, name: string) {
  updateElementClass(document.body, stat, name);
}

/*
    When a setting value is changed, detect its value and add/remove
    a classname related with that setting from the target element
*/
function updateClasses(state: RootState) {
  // updateBodyClass(state.setting.isFixed, 'layout-fixed');
  // updateBodyClass(state.setting.isBoxed, 'layout-boxed');
  // updateBodyClass(state.setting.isGlobalNavCollapsed, 'aside-collapsed');
  // updateBodyClass(state.setting.isCollapsedText, 'aside-collapsed-text');
  // updateBodyClass(state.setting.isFloat, 'aside-float');
  // updateBodyClass(state.setting.asideHover, 'aside-hover');
  // updateBodyClass(state.setting.offsidebarOpen, 'offsidebar-open');
  // updateBodyClass(state.setting.asideToggled, 'aside-toggled');
  // // layout horizontal
  // updateBodyClass(state.setting.horizontal, 'layout-h');
  // apply change to the sidebar element
  updateElementClass(document.querySelector('.sidebar'), state.setting.asideScrollbar, 'show-scrollbar');
}

/*
    Hook into setting changes in order to change layout.
*/
function SettingPlugin(store: Store<RootState>) {
  // wait for dom ready
  document.addEventListener('DOMContentLoaded', () => updateClasses(store.state));

  store.subscribe((mutation, state) => {
    if (mutation.type === 'changeSetting' || mutation.type === 'toggleSetting') {
      updateClasses(state);
    }
  });
}

export default SettingPlugin;
