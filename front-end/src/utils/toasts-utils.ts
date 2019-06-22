import { Dispatch } from 'vuex';
import { ToastNotification } from '@/types/toasts-types';
import { ToastActions } from '@/store/modules/toasts';
import store from '../store/index';

export async function createToast(dispatch: Dispatch, toast: ToastNotification) {
  // TODO: Use this for logging errors? We can just check "toast.variant === warning"

  await dispatch(`toasts/${ToastActions.displayToast}`, toast, { root: true });
}

export async function globalDispatchToast(toast: ToastNotification) {
  await store.dispatch(`toasts/${ToastActions.displayToast}`, toast);
}
