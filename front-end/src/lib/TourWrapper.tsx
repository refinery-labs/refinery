import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop, Watch } from 'vue-property-decorator';
import { DemoTooltip } from '@/types/demo-walkthrough-types';
import { DemoWalkthroughStoreModule } from '@/store';

@Component
export default class TourWrapper extends Vue {
  @Prop({ required: true }) nextTooltip!: () => void;
  @Prop({ required: true }) steps!: DemoTooltip[];

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

    const formattedSteps = this.steps.map(step => {
      return {
        ...step,
        header: {
          title: step.header
        },
        content: step.body
      };
    });

    return (
      <div>
        <v-tour name="step" steps={formattedSteps} finish="next" options={options} callbacks={tourCallbacks} />
      </div>
    );
  }
}
