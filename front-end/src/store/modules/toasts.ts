import { Module } from 'vuex';
import uuid from 'uuid/v4';
import { RootState } from '../store-types';
import {
  ToastConfig,
  ToastLocation,
  ToastNotification,
  ToastVariant
} from '@/types/toasts-types';

// Enums
export enum ToastMutators {
  addToast = 'addToast',
  removeToast = 'removeToast',
  markToastShown = 'markToastShown'
}

export enum ToastActions {
  displayToast = 'displayToast'
}

// Types
export interface ToastPaneState {
  activeToasts: ToastConfig[];
}

// Initial State
const moduleState: ToastPaneState = {
  activeToasts: []
};

const ToastPaneModule: Module<ToastPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [ToastMutators.addToast](state, toast: ToastConfig) {
      state.activeToasts = [...state.activeToasts, toast];
    },
    [ToastMutators.removeToast](state, toast: ToastConfig) {
      state.activeToasts = state.activeToasts.filter(t => t.id !== toast.id);
    },
    [ToastMutators.markToastShown](state, toast: ToastConfig) {
      const toasts = state.activeToasts.filter(t => t.id !== toast.id);

      toasts.push({
        ...toast,
        shown: true
      });

      state.activeToasts = toasts;
    }
  },
  actions: {
    [ToastActions.displayToast](context, toast: ToastNotification) {
      if (!toast || !toast.content || !toast.title) {
        console.error('Tried to show invalid toast');
        return;
      }

      const newToast: ToastConfig = {
        variant: ToastVariant.default,
        toaster: ToastLocation.TopRight,
        ...toast,
        id: uuid(),
        autoHideDelay: 3000,
        shown: false,
        timestamp: new Date().getTime()
      };

      context.commit(ToastMutators.addToast, newToast);
    }
  }
};

export default ToastPaneModule;
