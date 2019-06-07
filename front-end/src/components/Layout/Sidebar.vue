<template>
  <aside class="aside-container">
    <!-- START Sidebar (left)-->
    <div class="aside-inner">
      <nav class="sidebar" data-sidebar-anyclick-close="">
        <!-- START sidebar nav-->
        <ul class="sidebar-nav sidebar-nav--extra-height">
          <!-- END user info-->
          <!-- Iterates over all sidebar items-->
          <!--          <template v-for="item in Menu">-->
          <!--            &lt;!&ndash; Heading &ndash;&gt;-->
          <!--            &lt;!&ndash;            <li class="nav-heading" v-if="item.heading">&ndash;&gt;-->
          <!--            &lt;!&ndash;              <span>{{ item.heading || "STUBBED" }}</span>&ndash;&gt;-->
          <!--            &lt;!&ndash;            </li>&ndash;&gt;-->
          <!--            &lt;!&ndash; Single Menu &ndash;&gt;-->
          <!--            &lt;!&ndash;            <router-link&ndash;&gt;-->
          <!--            &lt;!&ndash;              tag="li"&ndash;&gt;-->
          <!--            &lt;!&ndash;              :to="item.path"&ndash;&gt;-->
          <!--            &lt;!&ndash;              active-class="active"&ndash;&gt;-->
          <!--            &lt;!&ndash;              v-if="!item.heading && !item.submenu"&ndash;&gt;-->
          <!--            &lt;!&ndash;            >&ndash;&gt;-->
          <!--            &lt;!&ndash;              <a :title="tr(item.translate, item.name)">&ndash;&gt;-->
          <!--            &lt;!&ndash;                <span&ndash;&gt;-->
          <!--            &lt;!&ndash;                  v-if="item.label"&ndash;&gt;-->
          <!--            &lt;!&ndash;                  :class="'float-right badge badge-' + item.label.color"&ndash;&gt;-->
          <!--            &lt;!&ndash;                  >{{ item.label.value }}</span&ndash;&gt;-->
          <!--            &lt;!&ndash;                >&ndash;&gt;-->
          <!--            &lt;!&ndash;                <em :class="item.icon"></em>&ndash;&gt;-->
          <!--            &lt;!&ndash;                <span>{{ tr(item.translate, item.name) }}</span>&ndash;&gt;-->
          <!--            &lt;!&ndash;              </a>&ndash;&gt;-->
          <!--            &lt;!&ndash;            </router-link>&ndash;&gt;-->
          <!--            &lt;!&ndash; Menu With Subitems &ndash;&gt;-->
          <!--            &lt;!&ndash;            <li&ndash;&gt;-->
          <!--            &lt;!&ndash;              :class="routeActiveClass(getSubRoutes(item))"&ndash;&gt;-->
          <!--            &lt;!&ndash;              v-if="!item.heading && item.submenu"&ndash;&gt;-->
          <!--            &lt;!&ndash;            >&ndash;&gt;-->
          <!--            &lt;!&ndash;              <a&ndash;&gt;-->
          <!--            &lt;!&ndash;                :title="tr(item.translate, item.name)"&ndash;&gt;-->
          <!--            &lt;!&ndash;                @click.prevent="toggleItemCollapse(item.name)"&ndash;&gt;-->
          <!--            &lt;!&ndash;                href&ndash;&gt;-->
          <!--            &lt;!&ndash;              >&ndash;&gt;-->
          <!--            &lt;!&ndash;                <span&ndash;&gt;-->
          <!--            &lt;!&ndash;                  v-if="item.label"&ndash;&gt;-->
          <!--            &lt;!&ndash;                  :class="'float-right badge badge-' + item.label.color"&ndash;&gt;-->
          <!--            &lt;!&ndash;                  >{{ item.label.value }}</span&ndash;&gt;-->
          <!--            &lt;!&ndash;                >&ndash;&gt;-->
          <!--            &lt;!&ndash;                <em :class="item.icon"></em>&ndash;&gt;-->
          <!--            &lt;!&ndash;                <span>{{ tr(item.translate, item.name) }}</span>&ndash;&gt;-->
          <!--            &lt;!&ndash;              </a>&ndash;&gt;-->
          <!--            &lt;!&ndash;              <b-collapse&ndash;&gt;-->
          <!--            &lt;!&ndash;                tag="ul"&ndash;&gt;-->
          <!--            &lt;!&ndash;                class="sidebar-nav sidebar-subnav"&ndash;&gt;-->
          <!--            &lt;!&ndash;                id="item.name"&ndash;&gt;-->
          <!--            &lt;!&ndash;                v-model="collapse[item.name]"&ndash;&gt;-->
          <!--            &lt;!&ndash;              >&ndash;&gt;-->
          <!--            &lt;!&ndash;                &lt;!&ndash;<li bar={{true}} class="sidebar-subnav-header"></li>&ndash;&gt;&ndash;&gt;-->
          <!--            &lt;!&ndash;                &lt;!&ndash; not sure why my IDE craps out with the above li &ndash;&gt;&ndash;&gt;-->
          <!--            &lt;!&ndash;                <div class="sidebar-subnav-header"></div>&ndash;&gt;-->
          <!--            &lt;!&ndash;                <template v-for="sitem in item.submenu">&ndash;&gt;-->
          <!--            &lt;!&ndash;                  <router-link tag="li" :to="sitem.path" active-class="active">&ndash;&gt;-->
          <!--            &lt;!&ndash;                    <a :title="tr(sitem.translate, sitem.name)">&ndash;&gt;-->
          <!--            &lt;!&ndash;                      <span&ndash;&gt;-->
          <!--            &lt;!&ndash;                        v-if="sitem.label"&ndash;&gt;-->
          <!--            &lt;!&ndash;                        :class="'float-right badge badge-' + sitem.label.color"&ndash;&gt;-->
          <!--            &lt;!&ndash;                        >{{ sitem.label.value }}</span&ndash;&gt;-->
          <!--            &lt;!&ndash;                      >&ndash;&gt;-->
          <!--            &lt;!&ndash;                      <span>{{ tr(sitem.translate, sitem.name) }}</span>&ndash;&gt;-->
          <!--            &lt;!&ndash;                    </a>&ndash;&gt;-->
          <!--            &lt;!&ndash;                  </router-link>&ndash;&gt;-->
          <!--            &lt;!&ndash;                </template>&ndash;&gt;-->
          <!--            &lt;!&ndash;              </b-collapse>&ndash;&gt;-->
          <!--            &lt;!&ndash;            </li>&ndash;&gt;-->
          <!--          </template>-->
        </ul>
        <!-- END sidebar nav-->
      </nav>
    </div>
    <!-- END Sidebar (left)-->
  </aside>
</template>

<script>
import Vue from 'vue';
import { mapState } from 'vuex';
import SidebarRun from './Sidebar.run';
import { SidebarMenuItems as Menu } from '../../menu';
import { UserInterfaceSettings } from '../../store/store-types';

export default Vue.extend({
  name: 'Sidebar',
  data() {
    return {
      Menu,
      collapse: this.buildCollapseList()
    };
  },
  mounted() {
    SidebarRun(this.$router, this.closeSidebar.bind(this));
  },
  computed: {
    ...mapState({
      showUserBlock: state => state.setting.showUserBlock
    })
  },
  watch: {
    $route(to, from) {
      this.closeSidebar();
    }
  },
  methods: {
    closeSidebar() {
      this.$store.commit('changeSetting', {
        name: UserInterfaceSettings.asideToggled,
        value: false
      });
    },
    buildCollapseList() {
      /** prepare initial state of collapse menus. Doesnt allow same route names */
      let collapse = {};
      Menu.filter(({ heading }) => !heading).forEach(
        ({ name, path, submenu }) => {
          collapse[name] = this.isRouteActive(
            submenu ? submenu.map(({ path }) => path) : path
          );
        }
      );
      return collapse;
    },
    getSubRoutes(item) {
      return item.submenu.map(({ path }) => path);
    },
    // translate a key or return default values
    tr(key, defaultValue) {
      // TODO: Add i18n support
      // return key ? this.$t(key, {defaultValue: defaultValue}) : defaultValue;
      return defaultValue;
    },
    isRouteActive(paths) {
      paths = Array.isArray(paths) ? paths : [paths];
      return paths.some(p => this.$route.path.indexOf(p) > -1);
    },
    routeActiveClass(paths) {
      return { active: this.isRouteActive(paths) };
    },
    toggleItemCollapse(collapseName) {
      for (let c in this.collapse) {
        if (this.collapse[c] === true && c !== collapseName)
          this.collapse[c] = false;
      }
      this.collapse[collapseName] = !this.collapse[collapseName];
    }
  }
});
</script>
