<template>
  <aside class="offsidebar d-none" ref="sidebarElement">
    <b-tabs nav-class="nav-justified">
      <b-tab title="first" active>
        <template slot="title">
          <em class="icon-equalizer fa-lg"></em>
        </template>
        <h3 class="text-center text-thin mt-4">Settings</h3>

        <div class="p-2">
          <h4 class="text-muted text-thin">Layout</h4>
          <div class="clearfix">
            <p class="float-left">Fixed</p>
            <div class="float-right">
              <label class="switch">
                <input type="checkbox" name="isFixed" v-model="isFixed" />
                <span></span>
              </label>
            </div>
          </div>
          <div class="clearfix">
            <p class="float-left">Boxed</p>
            <div class="float-right">
              <label class="switch">
                <input type="checkbox" name="isBoxed" v-model="isBoxed" />
                <span></span>
              </label>
            </div>
          </div>
        </div>
        <div class="p-2">
          <h4 class="text-muted text-thin">Aside</h4>
          <div class="clearfix">
            <p class="float-left">Collapsed</p>
            <div class="float-right">
              <label class="switch">
                <input
                  type="checkbox"
                  name="isGlobalNavCollapsed"
                  v-model="isGlobalNavCollapsed"
                />
                <span></span>
              </label>
            </div>
          </div>
          <div class="clearfix">
            <p class="float-left">Collapsed Text</p>
            <div class="float-right">
              <label class="switch">
                <input
                  type="checkbox"
                  name="isCollapsedText"
                  v-model="isCollapsedText"
                />
                <span></span>
              </label>
            </div>
          </div>
          <div class="clearfix">
            <p class="float-left">Float</p>
            <div class="float-right">
              <label class="switch">
                <input type="checkbox" name="isFloat" v-model="isFloat" />
                <span></span>
              </label>
            </div>
          </div>
          <div class="clearfix">
            <p class="float-left">Hover</p>
            <div class="float-right">
              <label class="switch">
                <input type="checkbox" name="asideHover" v-model="asideHover" />
                <span></span>
              </label>
            </div>
          </div>
          <div class="clearfix">
            <p class="float-left">Show Scrollbar</p>
            <div class="float-right">
              <label class="switch">
                <input
                  type="checkbox"
                  name="asideScrollbar"
                  v-model="asideScrollbar"
                />
                <span></span>
              </label>
            </div>
          </div>
        </div>
      </b-tab>
      <b-tab title="second">
        <template slot="title">
          <em class="icon-user fa-lg"></em>
        </template>
        <h3 class="text-center text-thin mt-4">Connections</h3>
        <div class="list-group">
          <!-- START list title-->
          <div class="list-group-item border-0">
            <small class="text-muted">ONLINE</small>
          </div>
          <!-- END list title-->
          <div class="list-group-item list-group-item-action border-0">
            <div class="media">
              <img
                class="align-self-center mr-3 rounded-circle thumb48"
                src="img/user/05.jpg"
                alt="Image"
              />
              <div class="media-body text-truncate">
                <a href="#">
                  <strong>Juan Sims</strong>
                </a>
                <br />
                <small class="text-muted">Designeer</small>
              </div>
              <div class="ml-auto">
                <span class="circle bg-success circle-lg"></span>
              </div>
            </div>
          </div>
          <div class="list-group-item list-group-item-action border-0">
            <div class="media">
              <img
                class="align-self-center mr-3 rounded-circle thumb48"
                src="img/user/06.jpg"
                alt="Image"
              />
              <div class="media-body text-truncate">
                <a href="#">
                  <strong>Maureen Jenkins</strong>
                </a>
                <br />
                <small class="text-muted">Designeer</small>
              </div>
              <div class="ml-auto">
                <span class="circle bg-success circle-lg"></span>
              </div>
            </div>
          </div>
          <div class="list-group-item list-group-item-action border-0">
            <div class="media">
              <img
                class="align-self-center mr-3 rounded-circle thumb48"
                src="img/user/07.jpg"
                alt="Image"
              />
              <div class="media-body text-truncate">
                <a href="#">
                  <strong>Billie Dunn</strong>
                </a>
                <br />
                <small class="text-muted">Designeer</small>
              </div>
              <div class="ml-auto">
                <span class="circle bg-danger circle-lg"></span>
              </div>
            </div>
          </div>
          <div class="list-group-item list-group-item-action border-0">
            <div class="media">
              <img
                class="align-self-center mr-3 rounded-circle thumb48"
                src="img/user/08.jpg"
                alt="Image"
              />
              <div class="media-body text-truncate">
                <a href="#">
                  <strong>Tomothy Roberts</strong>
                </a>
                <br />
                <small class="text-muted">Designeer</small>
              </div>
              <div class="ml-auto">
                <span class="circle bg-warning circle-lg"></span>
              </div>
            </div>
          </div>
          <!-- START list title-->
          <div class="list-group-item border-0">
            <small class="text-muted">OFFLINE</small>
          </div>
          <!-- END list title-->
          <div class="list-group-item list-group-item-action border-0">
            <div class="media">
              <img
                class="align-self-center mr-3 rounded-circle thumb48"
                src="img/user/09.jpg"
                alt="Image"
              />
              <div class="media-body text-truncate">
                <a href="#">
                  <strong>Lawrence Robinson</strong>
                </a>
                <br />
                <small class="text-muted">Designeer</small>
              </div>
              <div class="ml-auto">
                <span class="circle bg-warning circle-lg"></span>
              </div>
            </div>
          </div>
          <div class="list-group-item list-group-item-action border-0">
            <div class="media">
              <img
                class="align-self-center mr-3 rounded-circle thumb48"
                src="img/user/10.jpg"
                alt="Image"
              />
              <div class="media-body text-truncate">
                <a href="#">
                  <strong>Tyrone Owens</strong>
                </a>
                <br />
                <small class="text-muted">Designeer</small>
              </div>
              <div class="ml-auto">
                <span class="circle bg-warning circle-lg"></span>
              </div>
            </div>
          </div>
        </div>
        <div class="px-3 py-4 text-center">
          <!-- Optional link to list more users-->
          <a class="btn btn-purple btn-sm" href="#" title="See more contacts">
            <strong>Load more..</strong>
          </a>
        </div>
        <!-- Extra items-->
        <div class="px-3 py-2">
          <p>
            <small class="text-muted">Tasks completion</small>
          </p>
          <div class="progress progress-xs m-0">
            <div
              class="progress-bar bg-success"
              role="progressbar"
              aria-valuenow="80"
              aria-valuemin="0"
              aria-valuemax="100"
              style="width: 80%"
            >
              <span class="sr-only">80% Complete</span>
            </div>
          </div>
        </div>
        <div class="px-3 py-2">
          <p>
            <small class="text-muted">Upload quota</small>
          </p>
          <div class="progress progress-xs m-0">
            <div
              class="progress-bar bg-warning"
              role="progressbar"
              aria-valuenow="40"
              aria-valuemin="0"
              aria-valuemax="100"
              style="width: 40%"
            >
              <span class="sr-only">40% Complete</span>
            </div>
          </div>
        </div>
      </b-tab>
    </b-tabs>
  </aside>
</template>

<script>
import { mapMutations, mapGetters } from "vuex";
import Vue from "vue";
import { UserInterfaceSettings } from "../../store/store-types";

export default Vue.extend({
  computed: {
    isFixed: {
      get() {
        return this.settings[UserInterfaceSettings.isFixed];
      },
      set(value) {
        this.changeSetting({ name: UserInterfaceSettings.isFixed, value });
      }
    },
    isBoxed: {
      get() {
        return this.settings[UserInterfaceSettings.isBoxed];
      },
      set(value) {
        this.changeSetting({ name: UserInterfaceSettings.isBoxed, value });
      }
    },
    isGlobalNavCollapsed: {
      get() {
        return this.settings[UserInterfaceSettings.isGlobalNavCollapsed];
      },
      set(value) {
        this.changeSetting({
          name: UserInterfaceSettings.isGlobalNavCollapsed,
          value
        });
      }
    },
    isCollapsedText: {
      get() {
        return this.settings[UserInterfaceSettings.isCollapsedText];
      },
      set(value) {
        this.changeSetting({
          name: UserInterfaceSettings.isCollapsedText,
          value
        });
      }
    },
    isFloat: {
      get() {
        return this.settings[UserInterfaceSettings.isFloat];
      },
      set(value) {
        this.changeSetting({ name: UserInterfaceSettings.isFloat, value });
      }
    },
    asideHover: {
      get() {
        return this.settings[UserInterfaceSettings.asideHover];
      },
      set(value) {
        this.changeSetting({ name: UserInterfaceSettings.asideHover, value });
      }
    },
    asideScrollbar: {
      get() {
        return this.settings[UserInterfaceSettings.asideScrollbar];
      },
      set(value) {
        this.changeSetting({
          name: UserInterfaceSettings.asideScrollbar,
          value
        });
      }
    },
    ...mapGetters(["settings"])
  },
  methods: {
    ...mapMutations(["changeSetting", "toggleSetting"])
  },
  mounted() {
    const sidebarElement = this.$refs.sidebarElement;

    if (!sidebarElement) {
      return;
    }

    // const sidebarHtmlElement = sidebarElement as HTMLElement;

    // unhide offsidebar on mounted
    sidebarElement.classList.remove("d-none");
  }
});
</script>
