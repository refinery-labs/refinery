import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import moment from 'moment';
import { DeploymentException, GetLatestProjectDeploymentResponse } from '@/types/api-types';
import { DeployProjectResult } from '@/types/project-editor-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps } from '@/types/component-types';
import { ProjectConfig } from '@/types/graph';

const project = namespace('project');
const deployment = namespace('deployment');

@Component
export default class DeployProjectPane extends Vue {
  @project.State isDeployingProject!: boolean;
  @project.State latestDeploymentState!: GetLatestProjectDeploymentResponse | null;
  @project.State deploymentError!: DeployProjectResult;
  @project.State hasProjectBeenModified!: boolean;
  @project.State openedProjectConfig!: ProjectConfig | null;
  @project.State shouldForceRedeploy!: boolean;

  @project.Mutation setForceRedeploy!: (forceRedeploy: boolean) => void;

  @project.Action deployProject!: () => void;
  @project.Action resetDeploymentPane!: () => void;
  @project.Action setWarmupConcurrencyLevel!: () => void;

  @deployment.Action openViewExecutionsPane!: () => void;

  public async deployProjectClicked(e: Event) {
    e.preventDefault();
    await this.deployProject();
    this.openViewExecutionsPane();
  }

  getDeploymentErrorText(errors: DeploymentException[]) {
    return errors
      .map(
        (error, i) =>
          `===== Error #${i + 1} =====
Name: ${error.name}
Type: ${error.type}
Exception: ${error.exception}


`
      )
      .join('');
  }

  public renderTooltips() {
    if (this.isDeployingProject) {
      return null;
    }

    const deployButtonMessage = 'Click to begin the deployment process';

    return (
      <div>
        <b-tooltip target={() => this.$refs.confirmDeployButton} placement="bottom" show={this.hasProjectBeenModified}>
          {deployButtonMessage}
        </b-tooltip>
      </div>
    );
  }

  private getWarmupConcurrencyLevel() {
    if (!this.openedProjectConfig || !this.openedProjectConfig.warmup_concurrency_level) {
      return 0;
    }
    return this.openedProjectConfig.warmup_concurrency_level;
  }

  public renderDeploymentDetails() {
    if (this.deploymentError) {
      const editorProps: EditorProps = {
        readOnly: true,
        content: this.getDeploymentErrorText(this.deploymentError),
        name: 'deployment-error',
        lang: 'text',
        extraClasses: 'height--100percent'
      };

      return (
        <div class="display--flex flex-direction--column">
          <h4 class="text-align--left">Deployment Error{this.deploymentError.length > 1 ? 's' : ''}:</h4>
          <div style="width: 40vw; min-width: 300px; height: 360px">
            <RefineryCodeEditor props={editorProps} />
          </div>
        </div>
      );
    }

    if (!this.latestDeploymentState) {
      return <h3>Waiting for data...</h3>;
    }

    if (!this.latestDeploymentState.result) {
      return (
        <div>
          <h3 style="max-width: 300px">This will create a new deploy for the project.</h3>
        </div>
      );
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
    const loadingClasses = {
      'whirl standard': !this.deploymentError && (this.isDeployingProject || !this.latestDeploymentState)
    };

    return (
      <div class={loadingClasses}>
        <b-form class="mb-2 mt-2 text-align--left deploy-pane-container" on={{ submit: this.deployProjectClicked }}>
          <div class="deploy-pane-container__content overflow--scroll-y-auto">{this.renderDeploymentDetails()}</div>

          <hr />
          <b-form-group
            style="max-width: 450px"
            description="Auto-warming will automatically invoke your Code Blocks every five minutes in order to keep them 'warm' for future invocations. This has the benefit of faster run times with the trade-off of extra cost for the warmup invocations."
          >
            <label class="d-block">Auto-Warm Deployed Code Blocks</label>
            <div class="input-group with-focus">
              <b-form-select value={this.getWarmupConcurrencyLevel()} on={{ change: this.setWarmupConcurrencyLevel }}>
                <option value={0}>No Auto-Warming</option>
                <option value={1}>Auto-Warming</option>
                <option value={2}>2x Concurrency Auto-Warming</option>
                <option value={3}>3x Concurrency Auto-Warming</option>
                <option value={4}>4x Concurrency Auto-Warming</option>
                <option value={5}>5x Concurrency Auto-Warming</option>
                <option value={6}>6x Concurrency Auto-Warming</option>
                <option value={7}>7x Concurrency Auto-Warming</option>
                <option value={8}>8x Concurrency Auto-Warming</option>
                <option value={9}>9x Concurrency Auto-Warming</option>
                <option value={10}>10x Concurrency Auto-Warming</option>
              </b-form-select>
            </div>
          </b-form-group>

          <b-form-group
            id="force-redeploy-input-group"
            description="Force redeploying this project will remove all currently deployed blocks and redeploy them."
          >
            <b-form-checkbox
              id="force-redeploy-input"
              name="force-redeploy-input"
              on={{ change: () => this.setForceRedeploy(!this.shouldForceRedeploy) }}
              checked={this.shouldForceRedeploy}
            >
              Force redeploy this project?
            </b-form-checkbox>
          </b-form-group>

          <div class="row mt-2">
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
                disabled={this.isDeployingProject}
              >
                {this.deploymentError ? 'Retry' : 'Confirm'} Deploy
              </b-button>
            </b-button-group>
          </div>
          {this.renderTooltips()}
        </b-form>
      </div>
    );
  }
}
