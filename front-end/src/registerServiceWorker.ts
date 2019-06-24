/* eslint-disable no-console */

import { register } from 'register-service-worker';
import { globalDispatchToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';

if (process.env.NODE_ENV === 'production') {
  const serviceWorkerBase = process.env.VUE_APP_SERVICE_WORKER_BASE || process.env.BASE_URL;
  register(`${serviceWorkerBase}service-worker.js`, {
    ready() {
      console.log(
        'App is being served from cache by a service worker.\n' + 'For more details, visit https://goo.gl/AFskqB'
      );
    },
    registered(registration) {
      console.log('Service worker has been registered.');
    },
    cached() {
      console.log('Content has been cached for offline use.');
    },
    updatefound() {
      console.log('New content is downloading.');
    },
    updated(registration) {
      globalDispatchToast({
        title: 'Update Available',
        content: 'Please refresh the page :)',
        variant: ToastVariant.info,
        specialForceRefresh: true
      });
      console.log('New content is available. Please refresh the page.');
      // let worker = registration.waiting;
      // worker.postMessage({action: 'skipWaiting'})
    },
    offline() {
      globalDispatchToast({
        title: 'No Connection Detected',
        content: 'Please ensure you have an internet connection. App is running in offline mode.',
        variant: ToastVariant.warning
      });
      console.log('No internet connection found. App is running in offline mode.');
    },
    error(error) {
      globalDispatchToast({
        title: 'Unknown Load Error',
        content:
          'App had trouble starting up. Try refreshing the page. If this error persists, clear your browser cache and/or contact support.',
        variant: ToastVariant.danger
      });
      console.error('Error during service worker registration:', error);
    }
  });
}
