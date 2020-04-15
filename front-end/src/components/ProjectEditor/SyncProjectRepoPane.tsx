import { CreateElement, VNode } from 'vue';
import Component, { mixins } from 'vue-class-component';
import { namespace } from 'vuex-class';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { SyncProjectRepoPaneStoreModule } from '@/store';
import { GitPushResult } from '@/store/modules/panes/sync-project-repo-pane';
import { branchNameBlacklistRegex, newBranchText } from '@/constants/project-editor-constants';
import CreateToastMixin from '@/mixins/CreateToastMixin';
import { Watch } from 'vue-property-decorator';

const syncProjectRepo = namespace('syncProjectRepo');

@Component
export default class SyncProjectRepoPane extends mixins(CreateToastMixin) {
  @syncProjectRepo.State gitPushResult!: GitPushResult | undefined;
  @syncProjectRepo.State remoteBranchName!: string;

  public showingGitStatusDetails: boolean = false;

  @Watch('gitPushResult')
  public async showGitPushErrors() {
    if (!SyncProjectRepoPaneStoreModule.getGitPushResult) {
      return;
    }

    if (SyncProjectRepoPaneStoreModule.getGitPushResult !== GitPushResult.Success) {
      this.displayErrorToast('Git push failure', SyncProjectRepoPaneStoreModule.getGitPushResultMessage);
      return;
    }
    this.displaySuccessToast('Git push success', SyncProjectRepoPaneStoreModule.getGitPushResultMessage);
    await SyncProjectRepoPaneStoreModule.clearGitPushResult();
  }

  @Watch('remoteBranchName')
  public async diffCompiledProject() {
    await SyncProjectRepoPaneStoreModule.diffCompiledProject();
  }

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
        size="xl max-width--800px"
        title="Git status details"
        visible={true}
      >
        <div style="height: 600px">
          <RefineryCodeEditor props={props} />
        </div>
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
            class="col-12"
            type="submit"
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

  public renderCommitButtons() {
    if (SyncProjectRepoPaneStoreModule.getGitPushResult === GitPushResult.UnableToFastForward) {
      return (
        <div>
          <b-button-group class="col-12">
            <b-button
              variant="primary"
              class="col-6"
              type="submit"
              disabled={SyncProjectRepoPaneStoreModule.isPushingToRepo}
              on={{ click: SyncProjectRepoPaneStoreModule.pushToRemoteBranch }}
            >
              Push to branch
            </b-button>
            <b-button
              variant="danger"
              class="col-6"
              type="submit"
              disabled={SyncProjectRepoPaneStoreModule.isPushingToRepo}
              on={{ click: SyncProjectRepoPaneStoreModule.forcePushToRemoteBranch }}
            >
              Force push
            </b-button>
          </b-button-group>
        </div>
      );
    }
    return (
      <div class="mt-2">
        <b-button
          variant="primary"
          class="col-12"
          type="submit"
          disabled={SyncProjectRepoPaneStoreModule.isPushingToRepo}
          on={{ click: SyncProjectRepoPaneStoreModule.pushToRemoteBranch }}
        >
          Push to branch
        </b-button>
      </div>
    );
  }

  public mounted() {
    // async diff project so the UI loads faster
    SyncProjectRepoPaneStoreModule.diffCompiledProject();
  }

  public render(h: CreateElement): VNode {
    const loadingClasses = {
      'whirl standard': !SyncProjectRepoPaneStoreModule.gitStatusResult,
      'text-align--left': true,
      'padding--normal': true,
      'sync-project-repo-container': true
    };

    const repoBranches = SyncProjectRepoPaneStoreModule.repoBranches;
    const selectRepoBranches = [...repoBranches, newBranchText].map(branch => {
      return { value: branch, text: branch };
    });
    const usingExistingBranch = repoBranches.includes(SyncProjectRepoPaneStoreModule.remoteBranchName);
    const currentBranch = SyncProjectRepoPaneStoreModule.remoteBranchName;
    const currentSelectedBranch = usingExistingBranch ? currentBranch : newBranchText;

    const validBranch = currentBranch !== '' ? !branchNameBlacklistRegex.test(currentBranch) : null;

    return (
      <div class={loadingClasses}>
        <div>
          <div class="padding--small">
            <label class="d-block">Branch Name:</label>
            <b-form-select
              on={{ input: SyncProjectRepoPaneStoreModule.setRemoteBranchName }}
              value={currentSelectedBranch}
              options={selectRepoBranches}
            />
          </div>
          {!usingExistingBranch && (
            <div class="padding--small">
              <b-form-input
                type="text"
                autofocus={true}
                required={true}
                state={validBranch}
                value={SyncProjectRepoPaneStoreModule.getRemoteBranchName}
                on={{ input: SyncProjectRepoPaneStoreModule.setNewRemoteBranchName }}
                placeholder="eg, new-feature"
              />
            </div>
          )}
        </div>

        <b-form-invalid-feedback class="padding--small" state={validBranch}>
          The entered branch name is not valid. Please refer to{' '}
          <a href="https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-check-ref-format.html" target="_blank">
            check-ref-format
          </a>{' '}
          for valid branch names.
        </b-form-invalid-feedback>

        <hr />

        {this.renderCommitButtons()}

        <hr />

        <div class="deploy-pane-container__content overflow--scroll-y-auto">{this.renderGitStatusDetails()}</div>

        {this.renderModal()}
      </div>
    );
  }
}
