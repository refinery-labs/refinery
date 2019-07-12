<template>
  <div v-bind:class="{ split: true, [`split-${direction}`]: true, [extraClasses]: !!extraClasses }">
    <slot></slot>
  </div>
</template>

<script lang="ts">
import Vue from 'vue';
import Component from 'vue-class-component';
import SplitJs from 'split.js';
import { Prop, Watch } from 'vue-property-decorator';

interface SplitInstanceData {
  elements: Array<string | HTMLElement>;
  sizes: number[];
  minSizes: any[];
  instance: SplitJs.Instance | null;
}

@Component
export default class SplitComponent extends Vue implements SplitInstanceData {
  elements: Array<string | HTMLElement> = [];
  instance: SplitJs.Instance | null = null;
  minSizes: any[] = [];
  sizes: number[] = [];

  @Prop({ required: true }) direction!: 'horizontal' | 'vertical';
  @Prop({ default: 8 }) gutterSize!: number;
  @Prop() extraClasses?: string;

  @Watch('direction')
  onDirectionChanged() {
    this.init();
  }

  @Watch('gutterSize')
  onGutterSizeChanged() {
    this.init();
  }

  mounted() {
    this.elements = [];
    this.sizes = [];
    this.minSizes = [];
    if (this.$slots && this.$slots.default) {
      this.$slots.default.forEach(vnode => {
        if (vnode && vnode.tag && vnode.tag.indexOf('SplitArea') > -1) {
          // vnode.componentOptions.propsData     ******** Get Prop data
          if (vnode.elm) {
            // @ts-ignore
            this.elements.push(vnode.elm);
          }

          if (!vnode.componentInstance) {
            return;
          }

          // @ts-ignore
          if (vnode.componentInstance.size !== null && vnode.componentInstance.size !== undefined) {
            // @ts-ignore
            this.sizes.push(vnode.componentInstance.size);
          }
          // @ts-ignore
          if (vnode.componentInstance.minSize !== null && vnode.componentInstance.minSize !== undefined) {
            // @ts-ignore
            this.minSizes.push(vnode.componentInstance.minSize);
          }
        }
      });
    }
    this.init();
  }

  init() {
    if (this.instance !== null) {
      this.instance.destroy();
      this.instance = null;
    }

    if (this.elements.length === 0) {
      return;
    }

    const direction =
      this.direction === 'horizontal' ? 'horizontal' : this.direction === 'vertical' ? 'vertical' : undefined;

    this.instance = SplitJs(this.elements, {
      direction: direction,
      sizes: this.sizes,
      minSize: this.minSizes,
      gutterSize: this.gutterSize,
      cursor: this.direction === 'horizontal' ? 'col-resize' : 'row-resize',
      onDrag: () => {
        this.$emit('onDrag', this.instance && this.instance.getSizes());
      },
      onDragStart: () => {
        this.$emit('onDragStart', this.instance && this.instance.getSizes());
      },
      onDragEnd: () => {
        this.$emit('onDragEnd', this.instance && this.instance.getSizes());
      }
    });
  }

  changeAreaSize() {
    this.sizes = [];
    this.minSizes = [];

    if (this.$slots && this.$slots.default) {
      this.$slots.default.forEach(vnode => {
        if (vnode && vnode.tag && vnode.tag.indexOf('SplitArea') > -1) {
          if (!vnode.componentInstance) {
            return;
          }

          // @ts-ignore
          if (vnode.componentInstance.size !== null && vnode.componentInstance.size !== undefined) {
            // @ts-ignore
            this.sizes.push(vnode.componentInstance.size);
          }

          // @ts-ignore
          if (vnode.componentInstance.minSize !== null && vnode.componentInstance.minSize !== undefined) {
            // @ts-ignore
            this.minSizes.push(vnode.componentInstance.minSize);
          }
        }
      });
    }
    this.init();
  }

  reset() {
    this.init();
  }

  getSizes() {
    return this.instance && this.instance.getSizes();
  }
}
</script>

<style lang="scss">
.split {
  -webkit-box-sizing: border-box;
  -moz-box-sizing: border-box;
  box-sizing: border-box;
  overflow-y: auto;
  overflow-x: hidden;
  height: 100%;
  width: 100%;

  &-vertical {
    flex-direction: column;
  }
}

.gutter {
  background-color: #eee;
  background-repeat: no-repeat;
  background-position: 50%;
}

.gutter.gutter-horizontal {
  cursor: col-resize;
  background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAeCAYAAADkftS9AAAAIklEQVQoU2M4c+bMfxAGAgYYmwGrIIiDjrELjpo5aiZeMwF+yNnOs5KSvgAAAABJRU5ErkJggg==');
}

.gutter.gutter-vertical {
  cursor: row-resize;
  background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAFAQMAAABo7865AAAABlBMVEVHcEzMzMzyAv2sAAAAAXRSTlMAQObYZgAAABBJREFUeF5jOAMEEAIEEFwAn3kMwcB6I2AAAAAASUVORK5CYII=');
}

.split.split-horizontal,
.gutter.gutter-horizontal {
  height: 100%;
  float: left;
}
</style>
