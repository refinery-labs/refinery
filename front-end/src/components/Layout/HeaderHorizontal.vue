<template>
  <header class="topnavbar-wrapper">
    <!-- START Top Navbar-->
    <nav class="navbar topnavbar navbar-expand-lg navbar-light">
      <!-- START navbar header-->
      <div class="navbar-header">
        <a class="navbar-brand" href="#/">
          <div class="brand-logo">
            <!--<img class="img-fluid" src="img/logo.png" alt="App Logo">-->
            <span class="main-logo">REFINERY</span>
          </div>
          <div class="brand-logo-collapsed">
            <img class="img-fluid" src="/img/logo.png" alt="App" />
          </div>
        </a>
        <b-navbar-toggle target="nav_collapse"></b-navbar-toggle>
      </div>
      <!-- END navbar header-->
      <!-- START Left navbar-->
      <b-collapse is-nav id="nav_collapse">
        <b-navbar-nav class="mr-auto flex-column flex-lg-row">
          <template v-for="item in Menu">
            <!-- Single items -->
            <!--            <b-nav-item v-if="!item.heading && !item.submenu" :to="item.path">-->
            <!--              {{ item.name }}-->
            <!--            </b-nav-item>-->
            <!-- Dropdown items -->
            <template v-if="!item.heading && item.submenu">
              <!--              <b-nav-item-dropdown :text="item.name" no-caret>-->
              <!--                <b-dropdown-item-->
              <!--                  v-for="sitem in item.submenu"-->
              <!--                  :to="sitem.path"-->
              <!--                  :key="sitem.path"-->
              <!--                >-->
              <!--                  {{ sitem.name }}-->
              <!--                </b-dropdown-item>-->
              <!--              </b-nav-item-dropdown>-->
            </template>
          </template>
        </b-navbar-nav>
        <!-- END Left navbar-->
        <!-- START Right Navbar-->
        <ul class="navbar-nav flex-row">
          <!-- START lock screen-->
          <li class="nav-item d-none d-md-block">
            <router-link class="nav-link" to="/lock" title="Lock screen">
              <em class="icon-lock"></em>
            </router-link>
          </li>
          <!-- END lock screen-->
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
                      <p class="m-0 text-muted text-sm">
                        You have 10 new emails
                      </p>
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
                    <span class="badge badge-danger ml-auto">14</span>
                  </span>
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
      </b-collapse>
      <HeaderSearch />
    </nav>
    <!-- END Top Navbar-->
  </header>
</template>

<script>
import { mapMutations } from 'vuex';
import HeaderSearch from '@/components/Layout/HeaderSearch';
import ToggleFullscreen from '@/components/Common/ToggleFullscreen';
import Menu from '../../menu.js';

export default {
  name: 'Header',
  components: {
    HeaderSearch,
    ToggleFullscreen
  },
  data() {
    return {
      Menu: Menu.slice(0, 4)
    };
  },
  methods: {
    ...mapMutations(['toggleSetting']),
    toggleOffsidebar() {
      this.toggleSetting('offsidebarOpen');
    }
  }
};
</script>
