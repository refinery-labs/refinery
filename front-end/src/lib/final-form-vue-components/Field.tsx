import { FieldState, fieldSubscriptionItems, FormApi } from 'final-form';
import { getChildren, composeFieldValidators, FieldValidator } from './utils';
import Component from 'vue-class-component';
import Vue from 'vue';
import { Inject, Prop } from 'vue-property-decorator';

@Component
export default class FinalFormField<FieldValues = object> extends Vue {
  fieldState!: FieldState<FieldValues>;

  /**
   * When invoked, unsubscribes from the Final Form subscription.
   */
  unsubscribe!: () => void;

  @Inject('finalForm') finalForm!: FormApi<FieldValues>;

  @Prop({ required: true })
  name!: string;

  @Prop()
  validate?: FieldValidator<FieldValues> | FieldValidator<FieldValues>[];

  @Prop({ default: () => ({}) })
  subscription!: object;

  created() {
    const subscription =
      this.subscription ||
      fieldSubscriptionItems.reduce(
        (result, key) => {
          result[key] = true;
          return result;
        },
        {} as { [key: string]: true }
      );

    this.unsubscribe = this.finalForm.registerField(
      this.name,
      fieldState => {
        this.fieldState = fieldState;
        this.$emit('change', fieldState);
      },
      subscription,
      // @ts-ignore
      {
        getValidator: Array.isArray(this.validate) ? composeFieldValidators(this.validate) : () => this.validate
      }
    );
  }

  fieldEvents() {
    return {
      input: (e: Event) => this.fieldState.change(e.target && (e.target as HTMLFormElement).value),
      blur: () => this.fieldState.blur(),
      focus: () => this.fieldState.focus()
    };
  }

  render() {
    const { blur, change, focus, value, name, ...meta } = this.fieldState;

    if (!this.$scopedSlots.default) {
      return null;
    }

    const children = this.$scopedSlots.default({
      events: this.fieldEvents,
      change,
      value,
      name,
      meta
    });

    const childArray = getChildren(children);

    if (childArray === undefined) {
      return null;
    }

    return childArray[0];
  }
}
