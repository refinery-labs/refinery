import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import OpenedProjectGraphContainer from '@/containers/OpenedProjectGraphContainer';
import OpenedProjectOverview from '@/views/ProjectsNestedViews/OpenedProjectOverview';

@Component
export default class ViewProject extends Vue {
  isGraphVisible() {
    return this.$route.name !== 'project';
  }

  renderGraph() {
    const hideGraph = this.isGraphVisible();

    const classes = {
      'graph-visibility': true,
      'graph-visibility--hidden': hideGraph,

      'flex-grow--1': true,
      'display--flex': true
    };

    return (
      <div class={classes}>
        <OpenedProjectOverview />
      </div>
    );
  }

  renderRouterContainer() {
    const hideRouter = !this.isGraphVisible();

    const classes = {
      'project-router-container': true,
      'project-router-container--hidden': hideRouter
    };

    return (
      <div class={classes}>
        <router-view />
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const basePath = `/p/${this.$route.params.projectId}`;

    return (
      <div class="view-project-page">
        <b-nav tabs justified>
          <b-nav-item exact to={basePath} active-nav-item-class="active">
            Overview
          </b-nav-item>
          <b-nav-item to={`${basePath}/deployments`}>Deployments</b-nav-item>
          <b-nav-item to={`${basePath}/usage`}>Usage</b-nav-item>
          <b-nav-item to={`${basePath}/settings`}>Settings</b-nav-item>
        </b-nav>

        <div class="view-project-page-content position--relative flex-grow--1 width--100percent height--100percent">
          {this.renderGraph()}

          {this.renderRouterContainer()}
        </div>
      </div>
    );
  }
}
