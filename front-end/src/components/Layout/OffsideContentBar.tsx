import Vue from 'vue';
import moment from 'moment';
import { Component, Watch } from 'vue-property-decorator';
import { Route } from 'vue-router';
import { UserInterfaceSettings } from '@/store/store-types';
import { Action, Getter, Mutation, namespace } from 'vuex-class';
import { ToastConfig } from '@/types/toasts-types';
import {KeyboardEditorMode, keyboardMapToAceConfigMap, SettingsAppStoreModule} from '@/store/modules/settings-app';

const toasts = namespace('toasts');

@Component
export default class OffsideContentBar extends Vue {
  @toasts.State activeToasts!: ToastConfig[];

  @Mutation toggleSettingOn!: (name: UserInterfaceSettings) => {};
  @Mutation toggleSettingOff!: (name: UserInterfaceSettings) => {};
  @Action closeGlobalNav!: () => {};

  @Watch('$route', { deep: true })
  private elementsModified(val: Route, oldVal: Route) {
    // Don't do this anymore because it causes a double hit to occur.
    // this.toggleGlobalNavOff();
  }

  public toggleGlobalNavOff() {
    this.closeGlobalNav();
  }

  mounted() {
    const sidebarElement = this.$refs.sidebarElement as HTMLElement;

    if (!sidebarElement) {
      return;
    }

    // unhide offsidebar on mounted
    sidebarElement.classList.remove('d-none');
  }

  renderEmptyNotifications() {
    if (this.activeToasts && this.activeToasts.length > 0) {
      return null;
    }

    return <h4 class="text-muted text-thin">No notification history to display...</h4>;
  }

  renderNotification(toast: ToastConfig) {
    const updatedTime = moment(toast.timestamp);
    const durationSinceUpdated = moment.duration(-moment().diff(updatedTime)).humanize(true);
    return (
      <div class="p-2">
        <div role="alert" aria-live="assertive" aria-atomic="true" class="b-toast b-toast-prepend">
          <div class="toast">
            <header class="toast-header">
              <strong class="mr-2">{toast.title}</strong>
            </header>
            <div class="toast-body">{toast.content}</div>
            <span class="toast-footer text-muted text-thin">{durationSinceUpdated}</span>
          </div>
        </div>
      </div>
    );
  }

  render() {
    const toasts = [];

    for (let i = this.activeToasts.length - 1; i >= 0; i--) {
      toasts.push(this.renderNotification(this.activeToasts[i]));
    }

    const onHandlers = {
      // Sets the current index to be active
      change: (mode: KeyboardEditorMode) => SettingsAppStoreModule.setKeyboardMode(mode)
    };

    const itemList = Object.keys(keyboardMapToAceConfigMap).map(key => ({
      value: key,
      text: key
    }));

    return (
      <aside class="offsidebar d-none" ref="sidebarElement">
        <b-tabs nav-class="nav-justified">
          <b-tab title="first" active>
            <template slot="title">
              <em class="icon-equalizer fa-lg" />
            </template>
            <h3 class="text-center text-thin mt-4">Notifications</h3>

            {this.renderEmptyNotifications()}
            {toasts}
          </b-tab>
          <b-tab title="second">
            <template slot="title">
              <em class="icon-user fa-lg" />
            </template>
            <h3 class="text-center text-thin mt-4">User Settings</h3>
            <div class="list-group">
              <b-form-group description="Keyboard mode for text editor blocks.">
                <label class="d-block">Editor Key Mode:</label>
                <b-form-select
                  class="padding--small mt-2 mb-2"
                  value={SettingsAppStoreModule.keyboardMode}
                  on={onHandlers}
                  options={itemList} />
              </b-form-group>
            </div>
          </b-tab>
        </b-tabs>
      </aside>
    );
  }
}
