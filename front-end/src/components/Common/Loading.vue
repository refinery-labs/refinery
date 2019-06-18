<template>
  <div class="container">
    <div v-if="show" class="overlay">
      <div class="loading-text">
        <div class="spinner-border text-primary" role="status">
          <span class="sr-only">Loading...</span>
        </div>
        <br />
        {{ label }}
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
  @Prop({ default: false, required: true }) show!: boolean;
}
</script>

<style scoped>
.container {
  position: relative;
  margin: 0px;
  max-width: unset;
}

.overlay {
  background-color: #f0f0f0;
  z-index: 9998;
  position: absolute;
  top: 0;
  left: 0;
  margin: 0;
  border: none;
  width: 100%;
  height: 100%;
  opacity: 0.9;
}

.loading-text {
  text-align: center;
  color: #000000;
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
