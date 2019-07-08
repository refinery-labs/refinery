import Vue from 'vue';
import Component from 'vue-class-component';

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

@Component
export default class EmitterMixin extends Vue {
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
}
