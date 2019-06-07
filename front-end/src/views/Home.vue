<template>
  <div class="home">
    <h2>Welcome to Refinery!</h2>
    <router-link to="/projects">View Projects</router-link>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component
export default class Home extends Vue {}
</script>
