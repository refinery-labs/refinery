import { Dispatch } from 'vuex';
import { ToastNotification, ToastNotificationConfig } from '@/types/toasts-types';
import { ToastActions } from '@/store/modules/toasts';
import store from '../store/index';

function toastConfigToNotifcation(toast: ToastNotificationConfig): ToastNotification {
  return {
    noAutoHide: false,
    ...toast
  };
}

export async function createToast(dispatch: Dispatch, toast: ToastNotificationConfig) {
  // TODO: Use this for logging errors? We can just check "toast.variant === warning"

  await dispatch(`toasts/${ToastActions.displayToast}`, toastConfigToNotifcation(toast), { root: true });
}

export async function globalDispatchToast(toast: ToastNotificationConfig) {
  await store.dispatch(`toasts/${ToastActions.displayToast}`, toastConfigToNotifcation(toast));
}
