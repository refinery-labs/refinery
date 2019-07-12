<template>
  <div v-bind:class="{ 'loading-helper__container': true, [classes]: classes }">
    <div v-if="show" v-bind:class="{ 'loading-helper__overlay': true, 'loading-helper__overlay--dark': dark }">
      <div class="loading-helper__loading-text">
        <div class="spinner-border text-primary" role="status">
          <span class="sr-only">Loading...</span>
        </div>
        <div v-if="showLabel">
          {{ label }}
        </div>
      </div>
    </div>
    <slot></slot>
  </div>
</template>

<script lang="ts">
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import Vue from 'vue';
import { LoadingContainerProps } from '@/types/component-types';

@Component
export default class LoadingContainer extends Vue implements LoadingContainerProps {
  @Prop({ default: 'Loading...' }) label!: string;
  @Prop({ default: false }) dark?: boolean;
  @Prop({ default: true }) showLabel?: boolean;
  @Prop({ default: false, required: true }) show!: boolean;
  @Prop() classes?: string;
}
</script>

<style scoped lang="scss">
.loading-helper__container {
  position: relative;
  margin: 0;
  max-width: unset;
}

.loading-helper__overlay {
  background-color: #f0f0f0;
  color: #000000;
  z-index: 9998;
  position: absolute;
  top: 0;
  left: 0;
  margin: 0;
  border: none;
  width: 100%;
  height: 100%;
  opacity: 0.9;
  &--dark {
    background-color: #333;
    color: #fff;
    opacity: 0.7;
  }
}

.loading-helper__loading-text {
  text-align: center;
  z-index: 9999;
  top: 50%;
  transform: translateY(-50%);
  left: 0;
  bottom: 0;
  margin: auto;
  position: relative;
  font-weight: bold;
  font-size: 16px;
}
</style>
