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
