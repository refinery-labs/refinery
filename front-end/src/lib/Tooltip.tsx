import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import { HTMLTooltip } from '@/types/demo-walkthrough-types';

import '@/styles/tooltip.scss';
import PopperJS from 'popper.js';
import RefineryMarkdown from '@/components/Common/RefineryMarkdown';

@Component
export default class Tooltip extends Vue {
  @Prop({ required: true }) nextTooltip!: () => void;
  @Prop({ required: true }) skipTooltips!: () => void;
  @Prop({ required: true }) step!: HTMLTooltip;

  setupTooltip() {
    if (this.step === undefined) {
      return;
    }

    setTimeout(() => {
      const config = this.step.config;
      const target = document.querySelector(this.step.config.htmlSelector);
      const element = this.$refs['demo-tooltip'] as Element;

      if (target !== null && element !== undefined) {
        target.scrollIntoView({ behavior: 'smooth' });

        const placement = (config ? config.placement : 'bottom') as PopperJS.Placement;
        const options = {
          placement: placement
        };

        new PopperJS(target, element, options);
        element.classList.remove('v-step-hidden');
      }
    }, 0);
  }

  mounted() {
    this.setupTooltip();
  }

  onNext() {
    const element = this.$refs['demo-tooltip'] as Element;
    if (element !== undefined) {
      element.classList.add('v-step-hidden');
    }

    this.nextTooltip();
    this.setupTooltip();
  }

  onSkip() {
    this.skipTooltips();
  }

  render() {
    const contentMarkdown = {
      content: this.step.body
    };

    return (
      <div class="v-step v-step-hidden" ref="demo-tooltip">
        <div class="v-step__header">{this.step.header}</div>
        <div class="v-step__content">
          <RefineryMarkdown props={contentMarkdown} />
        </div>

        <div class="v-step__buttons">
          <button class="v-step__button v-step__button-skip" onclick={this.onSkip}>
            end
          </button>
          <button class="v-step__button v-step__button-stop" onclick={this.onNext}>
            continue
          </button>
        </div>

        <div class="v-step__arrow v-step__arrow--dark" />
      </div>
    );
  }
}
