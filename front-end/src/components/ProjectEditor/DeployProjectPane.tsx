import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import moment from 'moment';
import {GetLatestProjectDeploymentResponse} from '@/types/api-types';

const project = namespace('project');

@Component
export default class DeployProjectPane extends Vue {
  @project.State isDeployingProject!: boolean;
  @project.State latestDeploymentState!: GetLatestProjectDeploymentResponse | null;
  @project.State deploymentError!: string | null;

  @project.Action deployProject!: () => void;
  @project.Action resetDeploymentPane!: () => void;

  public deployProjectClicked(e: Event) {
    e.preventDefault();
    this.deployProject();
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
      return (
        <span>Waiting for data...</span>
      );
    }

    if (!this.latestDeploymentState.deployment_json) {
      return (
        <span>This will create a new deploy for the project.</span>
      );
    }

    return (
      <div class="display--flex flex-direction--column">
        <label class="text-muted text-align--left">Existing Deployment:</label>
        <span>Timestamp: {moment(this.latestDeploymentState.timestamp).toISOString()}</span>
      </div>
    );
  }

  public render(h: CreateElement): VNode {

    const formClasses = {
      'mb-3 mt-3 text-align--left deploy-pane-container': true,
      'whirl standard': !this.latestDeploymentState
    };

    return (
      <b-form class={formClasses} on={{ submit: this.deployProjectClicked }}>
        <div class="deploy-pane-container__content overflow--scroll-y-auto">
          {this.renderDeploymentDetails()}
        </div>
        <div class="row deploy-pane-container__bottom-buttons">
          <b-button-group class="col-12">
            <b-button variant="secondary" class="col-6" on={{ click: this.resetDeploymentPane }}>
              Cancel Deploy
            </b-button>
            <b-button variant="primary" class="col-6" type="submit">
              Confirm Deploy
            </b-button>
          </b-button-group>
        </div>
      </b-form>
    );
  }
}
