import { createForm, FormApi, FormState, formSubscriptionItems, ValidationErrors } from 'final-form';
import Vue, { ComponentOptions, CreateElement, VNode } from 'vue';
import { getChildren, composeFormValidators, ValidatorResult, FieldValidator } from './utils';
import Component from 'vue-class-component';
import { Prop, Provide, Watch } from 'vue-property-decorator';

const defaultSubscription = formSubscriptionItems.reduce(
  (result, key) => {
    result[key] = true;
    return result;
  },
  {} as { [key: string]: true }
);

@Component
export default class FinalForm<FormValues = object> extends Vue {
  /**
   * Instance of Final Form that will be injected to child fields.
   */
  finalForm!: FormApi<FormValues>;

  formState: FormState<FormValues> | null = null;

  /**
   * When invoked, unsubscribes from the Final Form subscription.
   */
  unsubscribe!: () => void;

  @Prop({ default: () => ({}) })
  initialValues!: FormValues;

  @Prop({ default: () => () => {} })
  submit!: () => void;

  @Prop({ default: () => ({}) })
  subscription!: object;

  // Can accept either an individual validator, or an array of validators. This syntax is unfortunately very verbose :(
  @Prop()
  validate?: FieldValidator<FormValues> | FieldValidator<FormValues>[];

  @Provide('finalForm') finalFormProvider = 'finalForm';

  constructor() {
    super();

    this.finalForm = createForm({
      onSubmit: this.submit,
      initialValues: this.initialValues,
      validate: Array.isArray(this.validate) ? composeFormValidators(this.validate) : this.validate
    });
  }

  created() {
    this.unsubscribe = this.finalForm.subscribe(state => {
      this.formState = state;
      this.$emit('change', state);
    }, this.subscription || defaultSubscription);
  }

  beforeDestroy() {
    this.unsubscribe();
  }

  handleSubmit(e: Event) {
    e && e.preventDefault();
    this.finalForm.submit();
  }

  render(h: CreateElement): VNode | VNode[] | undefined {
    const children = this.$scopedSlots.default
      ? this.$scopedSlots.default(
          Object.assign({}, this.formState, {
            handleSubmit: this.handleSubmit,
            mutators: this.finalForm.mutators,
            batch: this.finalForm.batch,
            blur: this.finalForm.blur,
            change: this.finalForm.change,
            focus: this.finalForm.focus,
            initialize: this.finalForm.initialize,
            reset: this.finalForm.reset
          })
        )
      : this.$slots.default;

    return h('div', undefined, getChildren(children));
  }
}
