<template>
  <component :is="tag" v-bind="$props" @click="handleClick">
    <em :class="iconClass"></em>
  </component>
</template>

<script>
// FULLSCREEN
// -----------------------------------
import screenfull from 'screenfull';

const FULLSCREEN_ON_ICON = 'fa fa-expand';
const FULLSCREEN_OFF_ICON = 'fa fa-compress';

export default {
  name: 'ToggleFullscreen',
  props: {
    tag: {
      type: String,
      default: 'A'
    }
  },
  data() {
    return {
      iconClass: FULLSCREEN_ON_ICON
    };
  },
  mounted() {
    // Not supported under IE
    const ua = window.navigator.userAgent;
    if (ua.indexOf('MSIE ') > 0 || !!ua.match(/Trident.*rv:11\./)) {
      this.$el.classList.add('d-none');
    }
  },
  methods: {
    handleClick: function(e) {
      e.preventDefault();

      if (screenfull.enabled) {
        screenfull.toggle();

        this.toggleFSIcon();
      } else {
        console.log('Fullscreen not enabled');
      }
    },
    toggleFSIcon() {
      this.iconClass = screenfull.isFullscreen ? FULLSCREEN_ON_ICON : FULLSCREEN_OFF_ICON;
    }
  }
};
</script>
