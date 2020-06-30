import { Module } from 'vuex';
import uuid from 'uuid/v4';
import { RootState } from '../store-types';
import { ToastConfig, ToastLocation, ToastNotification, ToastVariant } from '@/types/toasts-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { AuthWithGithubRequest, AuthWithGithubResponse } from '@/types/api-types';
import { API_ENDPOINT } from '@/constants/api-constants';
import { AllProjectsActions } from '@/store/modules/all-projects';

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

      const toastDelay = !toast.noAutoHide ? { autoHideDelay: 3000 } : {};

      const newToast: ToastConfig = {
        variant: ToastVariant.default,
        toaster: ToastLocation.TopRight,
        ...toast,
        ...toastDelay,
        id: uuid(),
        shown: false,
        timestamp: new Date().getTime()
      };

      context.commit(ToastMutators.addToast, newToast);
    }
  }
};

export default ToastPaneModule;
