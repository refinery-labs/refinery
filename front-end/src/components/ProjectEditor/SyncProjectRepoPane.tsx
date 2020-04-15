import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import moment from 'moment';
import { DeploymentException, GetLatestProjectDeploymentResponse } from '@/types/api-types';
import { DeployProjectResult, SIDEBAR_PANE } from '@/types/project-editor-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps } from '@/types/component-types';
import { ProjectConfig } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { SyncProjectRepoPaneStoreModule } from '@/store';
import { savedBlockTitles } from '@/constants/saved-block-constants';
import { GitPushResult } from '@/store/modules/panes/sync-project-repo-pane';

const project = namespace('project');
/*
 */

@Component
export default class SyncProjectRepoPane extends Vue {
  public showingGitStatusDetails: boolean = false;

  public renderModal() {
    if (!this.showingGitStatusDetails) {
      return null;
    }

    const modalOnHandlers = {
      hidden: () => (this.showingGitStatusDetails = false)
    };

    const props = {
      name: 'Git Status',
      lang: 'text',
      content: SyncProjectRepoPaneStoreModule.formattedGitStatusResult,
      readOnly: true,
      disableFullscreen: true,
      extraClasses: 'height--100percent'
    };

    return (
      <b-modal
        on={modalOnHandlers}
        hide-footer={true}
        no-close-on-esc={true}
        size="xl max-width--600px"
        title="Git status details"
        visible={true}
      >
        <RefineryCodeEditor props={props} />
      </b-modal>
    );
  }

  public renderGitStatusDetails() {
    if (SyncProjectRepoPaneStoreModule.gitStatusResult.length > 0) {
      const stats = SyncProjectRepoPaneStoreModule.getGitStatusStats;
      return (
        <div class="display--flex flex-direction--column">
          <h4 class="text-align--left">Git Status:</h4>
          <p>
            New files: {stats.newFiles}, Modified files: {stats.modifiedFiles}, Deleted files: {stats.deletedFiles}
          </p>
          <b-button
            variant="secondary"
            className="col-12"
            type="submit"
            ref="confirmDeployButton"
            on={{
              click: () => {
                this.showingGitStatusDetails = true;
              }
            }}
          >
            Details
          </b-button>
        </div>
      );
    }
    return <div />;
  }

  public renderGitPushErrors() {
    if (!SyncProjectRepoPaneStoreModule.isGitPushResultSet) {
      return <div />;
    }

    return (
      <div>
        <p>{SyncProjectRepoPaneStoreModule.getGitPushResultMessage}</p>
      </div>
    );
  }

  public renderCommitButtons() {
    if (SyncProjectRepoPaneStoreModule.getGitPushResult === GitPushResult.UnableToFastForward) {
      return (
        <div>
          <b-button
            variant="primary"
            className="col-6"
            type="submit"
            ref="confirmDeployButton"
            on={{ click: SyncProjectRepoPaneStoreModule.pushToRemoteBranch }}
          >
            Push to branch
          </b-button>
          <b-button
            variant="danger"
            className="col-6"
            type="submit"
            ref="confirmDeployButton"
            on={{ click: SyncProjectRepoPaneStoreModule.forcePushToRemoteBranch }}
          >
            Force push to branch
          </b-button>
        </div>
      );
    }
    return (
      <div>
        <b-button
          variant="primary"
          className="col-12"
          type="submit"
          ref="confirmDeployButton"
          on={{ click: SyncProjectRepoPaneStoreModule.pushToRemoteBranch }}
        >
          Push to branch
        </b-button>
      </div>
    );
  }

  public async mounted() {
    // async diff project so the UI loads faster
    SyncProjectRepoPaneStoreModule.diffCompiledProject();
  }

  public render(h: CreateElement): VNode {
    const loadingClasses = {
      'whirl standard': !SyncProjectRepoPaneStoreModule.gitStatusResult,
      'text-align--left': true,
      'padding--normal': true
    };

    return (
      <div class={loadingClasses}>
        <label class="d-block">Branch Name:</label>
        <b-form-input
          type="text"
          autofocus={true}
          required={true}
          value={SyncProjectRepoPaneStoreModule.remoteBranchName}
          on={{ input: SyncProjectRepoPaneStoreModule.setRemoteBranchName }}
          placeholder="eg, new-feature"
        />
        <b-form-select
          on={{ input: SyncProjectRepoPaneStoreModule.setRemoteBranchName }}
          value={SyncProjectRepoPaneStoreModule.remoteBranchName}
          options={SyncProjectRepoPaneStoreModule.getRepoBranches}
        />

        {this.renderGitPushErrors()}

        <hr />

        {this.renderCommitButtons()}

        <hr />

        <div class="deploy-pane-container__content overflow--scroll-y-auto">{this.renderGitStatusDetails()}</div>

        {this.renderModal()}
      </div>
    );
  }
}
