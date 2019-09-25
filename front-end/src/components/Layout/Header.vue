<template>
  <header class="topnavbar-wrapper">
    <!-- START Top Navbar-->
    <nav class="navbar topnavbar">
      <!-- START navbar header-->
      <div class="navbar-header">
        <router-link class="navbar-brand" to="/projects" v-if="authenticated">
          <div class="brand-logo">
            <img class="img-fluid" src="../../../public/img/logo-icon.png" alt="App" style="height: 35px" />
          </div>
          <div class="brand-logo-collapsed">
            <img
              class="img-fluid"
              style="max-width: 35px; max-height: 35px"
              src="../../../public/img/logo-icon.png"
              alt="Refinery - The World's First Drag-and-Drop Serverless IDE!"
            />
          </div>
        </router-link>

        <a class="navbar-brand" href="https://www.refinery.io/" target="_blank" v-else>
          <div class="brand-logo">
            <img class="img-fluid" src="../../../public/img/logo-icon.png" alt="App" style="height: 35px" />
          </div>
          <div class="brand-logo-collapsed">
            <img
              class="img-fluid"
              style="max-width: 35px; max-height: 35px"
              src="../../../public/img/logo-icon.png"
              alt="Refinery - The World's First Drag-and-Drop Serverless IDE!"
            />
          </div>
        </a>
      </div>
      <!-- END navbar header-->
      <!-- START Left navbar-->
      <ul class="navbar-nav mr-auto flex-row">
        <li class="nav-item">
          <!-- Button used to collapse the left sidebar. Only visible on tablet and desktops-->
          <a class="nav-link d-none d-md-block d-lg-block d-xl-block" @click.prevent="toggleGlobalNavCollapsed">
            <em class="fas fa-bars"></em>
          </a>
          <!-- Button to show/hide the sidebar on mobile. Visible on mobile only.-->
          <a href="" class="nav-link sidebar-toggle d-md-none" @click.prevent="toggleGlobalNavCollapsed">
            <em class="fas fa-bars"></em>
          </a>
        </li>
        <!-- START User avatar toggle-->
        <!--
        <li class="nav-item d-none d-md-block">
          <a class="nav-link" @click.prevent="toggleUserBlock">
            <em class="icon-user"></em>
          </a>
        </li>
        -->
        <!-- END User avatar toggle-->
        <!-- START lock screen-->
        <!--
        <li class="nav-item d-none d-md-block">
          <router-link class="nav-link" to="/lock" title="Lock screen">
            <em class="icon-lock"></em>
          </router-link>
        </li>
        -->
        <!-- END lock screen-->
      </ul>
      <!-- END Left navbar-->
      <!-- START Right Navbar-->
      <ul class="navbar-nav flex-row">
        <!-- Search icon-->
        <!--
        <li class="nav-item">
          <a class="nav-link" href="#" data-search-open="">
            <em class="icon-magnifier"></em>
          </a>
        </li>
        -->
        <!-- Fullscreen (only desktops)-->
        <li class="nav-item">
          <a href="" to="Live Chat" class="nav-link intercom-open-chat-button">
            <i class="fas fa-headset"></i>
            <span class="hide-on-mobile"> Live Chat</span>
          </a>
        </li>
        <li class="nav-item" v-if="authenticated">
          <a href="" class="nav-link" to="View Console Credentials" v-on:click="showAWSConsoleCredentialModal">
            <em class="fab fa-aws"></em><span class="hide-on-mobile"> View Console Credentials</span>
          </a>
        </li>
        <li class="nav-item d-none d-md-block">
          <ToggleFullscreen tag="A" class="nav-link" href="#" />
        </li>
        <!-- START Alert menu-->
        <!--
        <b-nav-item-dropdown class="dropdown-list" no-caret menuClass="animated flipInX" right>

          <template slot="button-content">
            <em class="icon-bell"></em>
            <span class="badge badge-danger">11</span>
          </template>
          <b-dropdown-item>
            <div class="list-group">
              <div class="list-group-item list-group-item-action">
                <div class="media">
                  <div class="align-self-start mr-2">
                    <em class="fab fa-twitter fa-2x text-info"></em>
                  </div>
                  <div class="media-body">
                    <p class="m-0">New followers</p>
                    <p class="m-0 text-muted text-sm">1 new follower</p>
                  </div>
                </div>
              </div>
              <div class="list-group-item list-group-item-action">
                <div class="media">
                  <div class="align-self-start mr-2">
                    <em class="fas fa-envelope fa-2x text-warning"></em>
                  </div>
                  <div class="media-body">
                    <p class="m-0">New e-mails</p>
                    <p class="m-0 text-muted text-sm">You have 10 new emails</p>
                  </div>
                </div>
              </div>
              <div class="list-group-item list-group-item-action">
                <div class="media">
                  <div class="align-self-start mr-2">
                    <em class="fas fa-tasks fa-2x text-success"></em>
                  </div>
                  <div class="media-body">
                    <p class="m-0">Pending Tasks</p>
                    <p class="m-0 text-muted text-sm">11 pending task</p>
                  </div>
                </div>
              </div>
              <div class="list-group-item list-group-item-action">
                <span class="d-flex align-items-center">
                  <span class="text-sm">More notifications</span>
                  <span class="badge badge-danger ml-auto">14</span> </span
                ><span class="text-sm">More notifications</span>
              </div>
            </div>
          </b-dropdown-item>
        </b-nav-item-dropdown>
        -->
        <!-- END Alert menu-->
        <!-- START Offsidebar button-->
        <li class="nav-item">
          <a href="" class="nav-link" @click.prevent.prevent="toggleOffsidebar">
            <em class="icon-notebook"></em>
          </a>
        </li>
        <!-- END Offsidebar.prevent menu-->
      </ul>
      <!-- END Right Navbar-->
      <HeaderSearch />
    </nav>
    <!-- END Top Navbar-->
  </header>
</template>

<script lang="ts">
import Component from 'vue-class-component';
import Vue from 'vue';
import HeaderSearch from '@/components/Layout/HeaderSearch.vue';
import ToggleFullscreen from '@/components/Common/ToggleFullscreen.vue';
import { Action, Mutation, namespace } from 'vuex-class';
import { UserInterfaceSettings } from '@/store/store-types';

const user = namespace('user');

@Component({
  components: {
    HeaderSearch,
    ToggleFullscreen
  }
})
export default class Header extends Vue {
  @user.State authenticated!: boolean;
  @Mutation toggleSetting!: (s: string) => void;
  @Action setIsAWSConsoleCredentialModalVisibleValue!: (s: boolean) => void;

  /**
   * Triggers a window resize event when clicked
   * for plugins that needs to be redrawed
   */
  resize(e: Event) {
    // all IE friendly dispatchEvent
    var evt = document.createEvent('UIEvents');
    // Not sure why this doesn't work -- it's code from the boilerplate so just gonna ignore and move on!
    // @ts-ignore
    evt.initUIEvent('resize', true, false, window, 0);
    window.dispatchEvent(evt);
    // modern dispatchEvent way
    // window.dispatchEvent(new Event('resize'));
  }
  toggleOffsidebar() {
    this.toggleSetting(UserInterfaceSettings.offsidebarOpen);
  }
  toggleOffcanvas() {
    this.toggleSetting(UserInterfaceSettings.asideToggled);
  }
  toggleGlobalNavCollapsed() {
    this.toggleSetting(UserInterfaceSettings.isGlobalNavCollapsed);
    //this.resize();
  }
  toggleUserBlock() {
    this.toggleSetting(UserInterfaceSettings.showUserBlock);
  }
  async showAWSConsoleCredentialModal(e: Event) {
    e.preventDefault();
    await this.setIsAWSConsoleCredentialModalVisibleValue(true);
  }
}
</script>
