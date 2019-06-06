import {Dispatch} from 'vuex';
import {ToastNotification} from '@/types/toasts-types';
import {ToastActions} from '@/store/modules/toasts';

export async function createToast(dispatch: Dispatch, toast: ToastNotification) {
  await dispatch(`toasts/${ToastActions.displayToast}`, toast, {root: true});
}
