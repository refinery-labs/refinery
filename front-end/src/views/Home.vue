<template>
  <div class="home">
    <h1>Welcome to Refinery!</h1>
    <br />
    <h3>Getting Started</h3>
    <div class="display--flex justify-content-center">
      <div class="text-align--left" style="max-width: 420px; margin-left: 20px; margin-right: 20px;">
        <p>
          We recommend taking a look at the
          <a href="https://docs.refinery.io/quickstart/intro/" target="_blank">Quick Start Guide</a>.
        </p>
        <p>
          You may also look at the example projects in your project list.
          <br />
          To find all of the projects in your account, <router-link to="/projects">click here</router-link>.
        </p>
        <p>
          If you would like to contact us for any reason, head over to the
          <router-link to="/help">Help Page</router-link> for more information.
        </p>
        <p>
          Even if you're just having a great day and want to share, we'd love to here from you!
        </p>
      </div>
    </div>
    <div class="display--flex justify-content-center">
      <div>
        <h3>Useful Links</h3>
        <ul class="text-align--left" style="max-width: 400px; font-size: 1.25em; margin-left: 36px">
          <li><a href="https://docs.refinery.io/quickstart/intro/" target="_blank">Quick Start Guide</a></li>
          <li><router-link to="/projects">View & Search Projects</router-link></li>
          <li><router-link to="/help">Help & Contact Page</router-link></li>
          <li><router-link to="/billing">Billing & Usage Information</router-link></li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component
export default class Home extends Vue {}
</script>
