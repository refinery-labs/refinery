import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import moment from 'moment';
import { GetLatestProjectDeploymentResponse } from '@/types/api-types';

const project = namespace('project');

@Component
export default class DeployProjectPane extends Vue {
  @project.State isDeployingProject!: boolean;
  @project.State latestDeploymentState!: GetLatestProjectDeploymentResponse | null;
  @project.State deploymentError!: string | null;
  @project.State hasProjectBeenModified!: boolean;

  @project.Action deployProject!: () => void;
  @project.Action resetDeploymentPane!: () => void;

  public deployProjectClicked(e: Event) {
    e.preventDefault();
    this.deployProject();
  }

  public renderTooltips() {
    const deployButtonMessage = this.hasProjectBeenModified
      ? 'You must save changes to project before you may deploy.'
      : 'Click to begin the deployment process';

    return (
      <div>
        <b-tooltip target={() => this.$refs.confirmDeployButton} placement="bottom" show={this.hasProjectBeenModified}>
          {deployButtonMessage}
        </b-tooltip>
      </div>
    );
  }

  public renderDeploymentDetails() {
    if (this.deploymentError) {
      return (
        <div class="display--flex flex-direction--column">
          <label class="text-muted text-align--left">Error:</label>
          <span class="text-danger">{this.deploymentError}</span>
        </div>
      );
    }

    if (!this.latestDeploymentState) {
      return <h3>Waiting for data...</h3>;
    }

    if (!this.latestDeploymentState.result) {
      return <h3>This will create a new deploy for the project.</h3>;
    }

    const displayTime = moment(this.latestDeploymentState.result.timestamp * 1000).format('LLLL');

    return (
      <div class="display--flex flex-direction--column text-align--left">
        <h4>
          Deploying this project will replace your current deployment!
          <br />
          <br />
          Are you sure you want to proceed?
        </h4>
        <label class="text-align--left">Last deployed: {displayTime}</label>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const formClasses = {
      'mb-3 mt-3 text-align--left deploy-pane-container': true,
      'whirl standard': !this.deploymentError && (this.isDeployingProject || !this.latestDeploymentState)
    };

    return (
      <b-form class={formClasses} on={{ submit: this.deployProjectClicked }}>
        <div class="deploy-pane-container__content overflow--scroll-y-auto">{this.renderDeploymentDetails()}</div>
        <div class="row deploy-pane-container__bottom-buttons">
          <b-button-group class="col-12">
            <b-button
              variant="secondary"
              class="col-6"
              on={{ click: this.resetDeploymentPane }}
              disabled={this.isDeployingProject}
            >
              Cancel Deploy
            </b-button>
            <b-button
              variant="primary"
              class="col-6"
              type="submit"
              ref="confirmDeployButton"
              disabled={this.isDeployingProject || this.hasProjectBeenModified}
            >
              Confirm Deploy
            </b-button>
          </b-button-group>
        </div>
        {this.renderTooltips()}
      </b-form>
    );
  }
}
