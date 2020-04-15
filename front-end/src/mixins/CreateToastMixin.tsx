import Vue from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { ToastNotification, ToastVariant } from '@/types/toasts-types';

const toasts = namespace('toasts');

@Component
export default class CreateToastMixin extends Vue {
  @toasts.Action displayToast!: (toast: ToastNotification) => void;

  public displayErrorToast(title: string, content: string) {
    this.displayToast({
      content,
      title,
      variant: ToastVariant.danger
    });
  }

  public displaySuccessToast(title: string, content: string) {
    this.displayToast({
      content,
      title,
      variant: ToastVariant.success
    });
  }
}
