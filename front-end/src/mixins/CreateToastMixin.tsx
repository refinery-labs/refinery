import Vue from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { ToastNotification, ToastVariant } from '@/types/toasts-types';

const toasts = namespace('toasts');

@Component
export default class CreateToastMixin extends Vue {
  @toasts.Action displayToast!: (toast: ToastNotification) => void;

  public displayErrorToast(title: string, content: string, autoHide?: boolean) {
    this.displayToast({
      content,
      title,
      variant: ToastVariant.danger,
      noAutoHide: autoHide !== undefined ? !autoHide : false,
      autoHideDelay: 3000
    });
  }

  public displaySuccessToast(title: string, content: string, autoHide?: boolean) {
    this.displayToast({
      content,
      title,
      variant: ToastVariant.success,
      noAutoHide: autoHide !== undefined ? !autoHide : false,
      autoHideDelay: 3000
    });
  }
}
