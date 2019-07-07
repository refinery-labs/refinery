function broadcast(context: Vue, componentName: string, eventName: string, params: string) {
  context.$children.forEach(child => {
    const name = child.$options.name;

    if (name === componentName) {
      // @ts-ignore
      child.$emit.apply(child, [eventName].concat(params));
    } else {
      // Todo If params is an empty array, the received will be undefined
      // @ts-ignore
      broadcast.apply(child, [componentName, eventName].concat([params]));
    }
  });
}

import Vue from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { ToastNotification, ToastVariant } from '@/types/toasts-types';

const toasts = namespace('toasts');

@Component
export default class EmitterMixin extends Vue {
  @toasts.Action displayToast!: (toast: ToastNotification) => void;

  dispatch(componentName: string, eventName: string, params: string[]) {
    let parent = this.$parent || this.$root;
    let name = parent.$options.name;

    while (parent && (!name || name !== componentName)) {
      parent = parent.$parent;

      if (parent) {
        name = parent.$options.name;
      }
    }
    if (parent) {
      // @ts-ignore
      parent.$emit.apply(parent, [eventName].concat(params));
    }
  }
  broadcast(componentName: string, eventName: string, params: string) {
    broadcast(this, componentName, eventName, params);
  }

  public displayErrorToast(title: string, content: string) {
    this.displayToast({
      content,
      title,
      variant: ToastVariant.danger
    });
  }
}
