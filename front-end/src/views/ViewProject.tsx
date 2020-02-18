import Vue, { CreateElement, VNode } from 'vue';
import Component, { mixins } from 'vue-class-component';
import OpenedProjectOverview from '@/views/ProjectsNestedViews/OpenedProjectOverview';
import { namespace } from 'vuex-class';
import { GetLatestProjectDeploymentResponse, GetSavedProjectRequest } from '@/types/api-types';
import { Route } from 'vue-router';
import CreateToastMixin from '@/mixins/CreateToastMixin';
import store from '@/store/index';
import { DeploymentViewMutators, ProjectViewActions, ProjectViewMutators } from '@/constants/store-constants';
import { tryParseInt } from '@/utils/number-utils';

const project = namespace('project');

@Component
export default class ViewProject extends mixins(CreateToastMixin) {
  @project.State latestDeploymentState!: GetLatestProjectDeploymentResponse | null;
  @project.Getter canSaveProject!: boolean;
  @project.Getter selectedResourceDirty!: boolean;
  @project.Action openProject!: (projectId: GetSavedProjectRequest) => {};
  @project.Action fetchLatestDeploymentState!: () => void;

  // This handles fetching the data for the UI upon route entry
  // Note: We don't block the call to next because that allows the user to "see" the UI first, including a loading animation.
  // Maybe that is a mistake... But it feels reasonable also. Could re-evaluate this in the future?
  public async beforeRouteEnter(to: Route, from: Route, next: () => void) {
    next();

    const openProjectRequest: GetSavedProjectRequest = {
      project_id: to.params.projectId
    };

    if (to.query.version !== undefined) {
      // Attempt to parse the version from the query string. If it fails, we will load the latest version anyway.
      openProjectRequest.version = tryParseInt(to.query.version, undefined);
    }

    await store.dispatch(`project/${ProjectViewActions.openProject}`, openProjectRequest);

    await store.dispatch(`project/${ProjectViewActions.fetchLatestDeploymentState}`);
  }

  public beforeRouteLeave(to: Route, from: Route, next: () => void) {
    if (this.canSaveProject || this.selectedResourceDirty) {
      this.displayErrorToast('Unable to Navigate', 'Please save the current project or resource before continuing.');
      return;
    }

    store.commit(`project/${ProjectViewMutators.resetState}`);
    store.commit(`deployment/${DeploymentViewMutators.resetState}`);
    next();
  }

  isGraphVisible() {
    return this.$route.name !== 'project';
  }

  renderGraph() {
    const hideGraph = this.isGraphVisible();

    const classes = {
      'graph-visibility': true,
      'graph-visibility--hidden': hideGraph,

      'graph-with-grid': true,
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
      'display--flex': true,
      'project-router-container--hidden': hideRouter
    };

    return (
      <div class={classes}>
        <router-view />
      </div>
    );
  }

  renderDeploymentsTab() {
    const basePath = `/p/${this.$route.params.projectId}`;
    const deploymentToolTip = 'You currently do not have anything deployed. Click "Deploy Project" to do so.';
    console.log(this.latestDeploymentState);

    if (!this.latestDeploymentState || !this.latestDeploymentState.result) {
      return (
        <b-nav-item ref="deploymentTab" to={`${basePath}/deployments`} disabled>
          Deployment
          <b-tooltip target={() => this.$refs.deploymentTab} placement="bottom">
            {deploymentToolTip}
          </b-tooltip>
        </b-nav-item>
      );
    }

    return (
      <b-nav-item ref="deploymentTab" to={`${basePath}/deployments`}>
        Deployment
      </b-nav-item>
    );
  }

  public render(h: CreateElement): VNode {
    const basePath = `/p/${this.$route.params.projectId}`;
    return (
      <div class="view-project-page">
        <b-nav tabs justified>
          <b-nav-item exact to={basePath} active-nav-item-class="active">
            Editor
          </b-nav-item>
          {this.renderDeploymentsTab()}
          {/*<b-nav-item to={`${basePath}/usage`}>Usage</b-nav-item>*/}
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
