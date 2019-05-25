<template>
  <aside class="aside-container">
    <!-- START Sidebar (left)-->
    <div class="aside-inner">
      <nav class="sidebar" data-sidebar-anyclick-close="">
        <!-- START sidebar nav-->
        <ul class="sidebar-nav sidebar-nav--extra-height">
          <!-- END user info-->
          <!-- Iterates over all sidebar items-->
          <template v-for="item in Menu">
            <!-- Heading -->
            <li class="nav-heading" v-if="item.heading">
              <span>{{item.heading || 'STUBBED'}}</span>
            </li>
            <!-- Single Menu -->
            <router-link tag="li" :to="item.path" active-class="active" v-if="!item.heading && !item.submenu">
              <a :title="tr(item.translate, item.name)">
                <span v-if="item.label" :class="'float-right badge badge-'+item.label.color">{{item.label.value}}</span>
                <em :class="item.icon"></em>
                <span>{{tr(item.translate, item.name)}}</span>
              </a>
            </router-link>
            <!-- Menu With Subitems -->
            <li :class="routeActiveClass(getSubRoutes(item))" v-if="!item.heading && item.submenu">
              <a :title="tr(item.translate, item.name)" @click.prevent="toggleItemCollapse(item.name)" href>
                <span v-if="item.label" :class="'float-right badge badge-'+item.label.color">{{item.label.value}}</span>
                <em :class="item.icon"></em>
                <span>{{tr(item.translate, item.name)}}</span>
              </a>
              <b-collapse tag="ul" class="sidebar-nav sidebar-subnav" id="item.name" v-model="collapse[item.name]">
                <!--<li bar={{true}} class="sidebar-subnav-header"></li>-->
                <!-- not sure why my IDE craps out with the above li -->
                <div class="sidebar-subnav-header"></div>
                <template v-for="sitem in item.submenu">
                  <router-link tag="li" :to="sitem.path" active-class="active">
                    <a :title="tr(sitem.translate, sitem.name)">
                      <span v-if="sitem.label" :class="'float-right badge badge-'+sitem.label.color">{{sitem.label.value}}</span>
                      <span>{{tr(sitem.translate, sitem.name)}}</span>
                    </a>
                  </router-link>
                </template>
              </b-collapse>
            </li>
          </template>
        </ul>
        <!-- END sidebar nav-->
      </nav>
    </div>
    <!-- END Sidebar (left)-->
  </aside>
</template>

<script>
    import Vue from 'vue';
    import {mapState} from 'vuex';
    import SidebarRun from './Sidebar.run';
    import {SidebarMenuItems as Menu} from '../../menu';
    import {UserInterfaceSettings} from '../../store/store-types';

    export default Vue.extend({
        name: 'Sidebar',
        data() {
            return {
                Menu,
                collapse: this.buildCollapseList()
            }
        },
        mounted() {
            SidebarRun(this.$router, this.closeSidebar.bind(this))
        },
        computed: {
            ...mapState({
                showUserBlock: state => state.setting.showUserBlock
            })
        },
        watch: {
            $route(to, from) {
                this.closeSidebar()
            }
        },
        methods: {
            closeSidebar() {
                this.$store.commit('changeSetting', {name: UserInterfaceSettings.asideToggled, value: false})
            },
            buildCollapseList() {
                /** prepare initial state of collapse menus. Doesnt allow same route names */
                let collapse = {};
                Menu
                    .filter(({heading}) => !heading)
                    .forEach(({name, path, submenu}) => {
                        collapse[name] = this.isRouteActive(submenu ? submenu.map(({path}) => path) : path)
                    });
                return collapse;
            },
            getSubRoutes(item) {
                return item.submenu.map(({path}) => path)
            },
            // translate a key or return default values
            tr(key, defaultValue) {
                // TODO: Add i18n support
                // return key ? this.$t(key, {defaultValue: defaultValue}) : defaultValue;
                return defaultValue;
            },
            isRouteActive(paths) {
                paths = Array.isArray(paths) ? paths : [paths];
                return paths.some(p => this.$route.path.indexOf(p) > -1)
            },
            routeActiveClass(paths) {
                return {'active': this.isRouteActive(paths)}
            },
            toggleItemCollapse(collapseName) {
                for (let c in this.collapse) {
                    if (this.collapse[c] === true && c !== collapseName)
                        this.collapse[c] = false
                }
                this.collapse[collapseName] = !this.collapse[collapseName]
            }

        }
    });
</script>