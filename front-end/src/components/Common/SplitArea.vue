<template>
  <div v-bind:class="classes" style="" ref="splitArea">
    <slot></slot>
  </div>
</template>

<script lang="ts">
  import Vue from 'vue';
  import Emitter from '../../mixins/emitter';

  export default Vue.extend({
    name: 'SplitArea',
    mixins: [Emitter],
    props: {
      size: {
        type: Number,
        default: 50
      },
      minSize: {
        type: Number,
        default: 100
      },
      positionRelative: {
        type: Boolean,
        default: false
      },
      extraClasses: {
        type: String,
        default: ''
      }
    },
    computed: {
      classes(): {} {
        // @ts-ignore
        const direction = this.$parent.direction;

        return {
          split: true,
          [`split-${direction}`]: direction,
          'position--relative': this.positionRelative,
          [this.extraClasses]: true
        };
      }
    },
    watch: {
      size(val) {
        // Gross reformatted library code
        if (!this.$parent) {
          return;
        }
        // @ts-ignore
        const parent: { changeAreaSize?: (() => void) | any } = this.$parent;

        if (!parent.changeAreaSize || typeof parent.changeAreaSize !== 'function') {
          return;
        }

        parent.changeAreaSize();

      },
      minSize(val) {
        // Gross reformatted library code
        if (!this.$parent) {
          return;
        }
        // @ts-ignore
        const parent: { changeAreaSize?: (() => void) | any } = this.$parent;

        if (!parent.changeAreaSize || typeof parent.changeAreaSize !== 'function') {
          return;
        }

        parent.changeAreaSize();
      }
    }
  });
</script>