<template>
  <header class="topnavbar-wrapper">
    <!-- START Top Navbar-->
    <nav class="navbar topnavbar">
      <!-- START navbar header-->
      <div class="navbar-header">
        <router-link class="navbar-brand" to="/">
          <div class="brand-logo">
            <!--<img class="img-fluid" src="img/logo.png" alt="App Logo">-->
            <span class="main-logo">REFINERY</span>
          </div>
          <div class="brand-logo-collapsed">
            <img
              class="img-fluid"
              style="max-width: 40px; max-height: 40px"
              src="/img/logo-icon.png"
              alt="Refinery - The World's First Drag-and-Drop Serverless IDE!"
            />
          </div>
        </router-link>
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
          <a href="" class="nav-link sidebar-toggle d-md-none" @click.prevent="toggleOffcanvas">
            <em class="fas fa-bars"></em>
          </a>
        </li>
        <!-- START User avatar toggle-->
        <li class="nav-item d-none d-md-block">
          <!-- Button used to collapse the left sidebar. Only visible on tablet and desktops-->
          <a class="nav-link" @click.prevent="toggleUserBlock">
            <em class="icon-user"></em>
          </a>
        </li>
        <!-- END User avatar toggle-->
        <!-- START lock screen-->
        <li class="nav-item d-none d-md-block">
          <router-link class="nav-link" to="/lock" title="Lock screen">
            <em class="icon-lock"></em>
          </router-link>
        </li>
        <!-- END lock screen-->
      </ul>
      <!-- END Left navbar-->
      <!-- START Right Navbar-->
      <ul class="navbar-nav flex-row">
        <!-- Search icon-->
        <li class="nav-item">
          <a class="nav-link" href="#" data-search-open="">
            <em class="icon-magnifier"></em>
          </a>
        </li>
        <!-- Fullscreen (only desktops)-->
        <li class="nav-item d-none d-md-block">
          <ToggleFullscreen tag="A" class="nav-link" href="#" />
        </li>
        <!-- START Alert menu-->
        <b-nav-item-dropdown class="dropdown-list" no-caret menuClass="animated flipInX" right>
          <template slot="button-content">
            <em class="icon-bell"></em>
            <span class="badge badge-danger">11</span>
          </template>
          <b-dropdown-item>
            <!-- START list group-->
            <div class="list-group">
              <!-- list item-->
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
              <!-- list item-->
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
              <!-- list item-->
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
              <!-- last list item-->
              <div class="list-group-item list-group-item-action">
                <span class="d-flex align-items-center">
                  <span class="text-sm">More notifications</span>
                  <span class="badge badge-danger ml-auto">14</span> </span
                ><span class="text-sm">More notifications</span>
              </div>
            </div>
            <!-- END list group-->
          </b-dropdown-item>
        </b-nav-item-dropdown>
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

<script>
import Vue from 'vue';
import { mapMutations } from 'vuex';
import HeaderSearch from './HeaderSearch';
import ToggleFullscreen from '../Common/ToggleFullscreen';
import { UserInterfaceSettings } from '../../store/store-types';

export default Vue.extend({
  name: 'Header',
  components: {
    HeaderSearch,
    ToggleFullscreen
  },
  methods: {
    /**
     * Triggers a window resize event when clicked
     * for plugins that needs to be redrawed
     */
    resize: e => {
      // all IE friendly dispatchEvent
      var evt = document.createEvent('UIEvents');
      evt.initUIEvent('resize', true, false, window, 0);
      window.dispatchEvent(evt);
      // modern dispatchEvent way
      // window.dispatchEvent(new Event('resize'));
    },
    ...mapMutations(['toggleSetting']),
    toggleOffsidebar() {
      this.toggleSetting(UserInterfaceSettings.offsidebarOpen);
    },
    toggleOffcanvas() {
      this.toggleSetting(UserInterfaceSettings.asideToggled);
    },
    toggleGlobalNavCollapsed() {
      this.toggleSetting(UserInterfaceSettings.isGlobalNavCollapsed);
      this.resize();
    },
    toggleUserBlock() {
      this.toggleSetting(UserInterfaceSettings.showUserBlock);
    }
  }
});
</script>
