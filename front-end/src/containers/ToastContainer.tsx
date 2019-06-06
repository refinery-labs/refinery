import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {
  namespace
} from 'vuex-class'
import {Prop, Watch} from 'vue-property-decorator';
import {ToastConfig} from '@/types/toasts-types';

const toasts = namespace('toasts');

@Component
export class ToastComponent extends Vue {

  @Prop({required: true}) activeToasts!: ToastConfig[];
  @Prop({required: true}) markToastShown!: (t: ToastConfig) => void;
  @Prop({required: true}) markToastDone!: (t: ToastConfig) => void;
  
  @Watch('activeToasts', {immediate: true})
  private activeToastsChanged(val: ToastConfig[], oldVal: ToastConfig[]) {
    if (val && oldVal && val === oldVal) {
      return;
    }
  
    val
      // Only grab toasts that have been "shown" already
      .filter(t => !t.shown)
      .forEach(t => {
        // Splits object properties such that "rest" contains everything except "content".
        const {content, ...rest} = t;
        
        // We don't have type definitions for this
        // @ts-ignore
  
        this.$bvToast.toast(content, rest);
  
        // Allows us to prevent the toast from showing up again.
        this.markToastShown(t);
      });
  }

  render() {
    return <span />
  }
}

@Component
export default class ToastContainer extends Vue {
  @toasts.State activeToasts!: ToastConfig[];
  
  @toasts.Mutation markToastShown!: (t: ToastConfig) => void;
  @toasts.Mutation removeToast!: (t: ToastConfig) => void;
  
  public render(h: CreateElement): VNode {
    return (
      <div class="toasts-container">
        <ToastComponent props={{
          activeToasts: this.activeToasts,
          markToastShown: this.markToastShown,
          markToastDone: this.removeToast
        }} />
      </div>
    );
  }
}
