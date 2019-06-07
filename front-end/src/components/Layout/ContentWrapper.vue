<template>
  <div class="content-wrapper">
    <div class="unwrap" v-if="unwrap">
      <slot></slot>
    </div>
    <slot v-else></slot>
  </div>
</template>

<script>
import Vue from 'vue';
export default Vue.extend({
  name: 'ContentWrapper',
  props: {
    unwrap: Boolean
  }
});
</script>
