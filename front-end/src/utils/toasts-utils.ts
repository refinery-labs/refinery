import { Dispatch } from 'vuex';
import { ToastNotification } from '@/types/toasts-types';
import { ToastActions } from '@/store/modules/toasts';

export async function createToast(dispatch: Dispatch, toast: ToastNotification) {
  // TODO: Use this for logging errors? We can just check "toast.variant === warning"

  await dispatch(`toasts/${ToastActions.displayToast}`, toast, { root: true });
}
