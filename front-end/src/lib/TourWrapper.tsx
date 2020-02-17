import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop, Watch } from 'vue-property-decorator';

@Component
export default class TourWrapper extends Vue {
  @Prop({ required: true }) nextTooltip!: () => void;
  @Prop({ required: true }) steps!: object[] | null;

  mounted() {
    // @ts-ignore
    this.$tours['step'].start();
  }

  onStop() {
    this.nextTooltip();
  }

  render() {
    const tourCallbacks = {
      onStop: this.onStop
    };
    const options = {
      labels: {
        buttonStop: 'continue'
      }
    };
    return (
      <div>
        <v-tour name="step" steps={this.steps} finish="next" options={options} callbacks={tourCallbacks} />
      </div>
    );
  }
}
