import Vue, { CreateElement, VNode } from 'vue';
import Component, { mixins } from 'vue-class-component';
import { namespace } from 'vuex-class';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { SyncProjectRepoPaneStoreModule } from '@/store';
import { GitPushResult } from '@/store/modules/panes/sync-project-repo-pane';
import { branchNameBlacklistRegex, newBranchText } from '@/constants/project-editor-constants';
import CreateToastMixin from '@/mixins/CreateToastMixin';
import { Watch } from 'vue-property-decorator';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { GitDiffInfo } from '@/repo-compiler/lib/git-types';
import Loading from '@/components/Common/Loading.vue';
import { LoadingContainerProps } from '@/types/component-types';

const syncProjectRepo = namespace('syncProjectRepo');

@Component
export default class SyncProjectRepoPane extends mixins(CreateToastMixin) {
  @syncProjectRepo.State gitPushResult!: GitPushResult | undefined;
  @syncProjectRepo.State remoteBranchName!: string;

  public showingGitStatusDetails: boolean = false;
  public forcePushModalVisible: boolean = false;
  private gitCommandResult: string = '';

  // TODO this should be in the store
  public gitDiffInfo: GitDiffInfo = { originalFiles: {}, changedFiles: {} };

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
    this.gitDiffInfo = await SyncProjectRepoPaneStoreModule.diffCompiledProject();
  }

  public async changeCurrentlyDiffedFile(file: string) {
    await SyncProjectRepoPaneStoreModule.setCurrentlyDiffedFile(file);
  }

  public getOriginalContent(currentlyDiffedFile: string | null): string {
    if (!currentlyDiffedFile) {
      return '';
    }

    const originalFileContent = this.gitDiffInfo.originalFiles[currentlyDiffedFile];
    if (!originalFileContent) {
      return '';
    }
    return originalFileContent;
  }

  public getNewContent(currentlyDiffedFile: string | null): string {
    if (!currentlyDiffedFile) {
      return '';
    }

    return this.gitDiffInfo.changedFiles[currentlyDiffedFile];
  }

  public renderModal() {
    if (!this.showingGitStatusDetails) {
      return null;
    }

    const modalOnHandlers = {
      hidden: () => (this.showingGitStatusDetails = false)
    };

    const diffFiles = Object.keys(this.gitDiffInfo.changedFiles).map(file => {
      return { value: file, text: file };
    });

    const currentlyDiffedFile = SyncProjectRepoPaneStoreModule.getCurrentlyDiffedFile;

    const originalContent = this.getOriginalContent(currentlyDiffedFile);
    const newContent = this.getNewContent(currentlyDiffedFile);

    const props = {
      name: `Git Status: ${currentlyDiffedFile}`,
      lang: 'text',
      readOnly: true,
      diffEditor: true,
      originalContent: originalContent,
      content: newContent
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
        <div>
          <div style="height: 600px">
            <RefineryCodeEditor props={props} />
          </div>
          <div class="margin-top--normal">
            <label class="d-block">Choose a file to view diff:</label>
            <b-form-select
              on={{ input: this.changeCurrentlyDiffedFile }}
              value={currentlyDiffedFile}
              options={diffFiles}
            />
          </div>
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

  public async forcePushToRepo() {
    await SyncProjectRepoPaneStoreModule.forcePushToRemoteBranch();
    this.forcePushModalVisible = false;
  }

  public showForcePushModal() {
    this.forcePushModalVisible = true;
  }

  public renderForcePushWarning() {
    if (!this.forcePushModalVisible) {
      return null;
    }

    const modalOnHandlers = {
      hidden: () => {
        this.forcePushModalVisible = false;
      }
    };

    return (
      <b-modal
        on={modalOnHandlers}
        hide-footer={true}
        title={`Force push to the branch ${SyncProjectRepoPaneStoreModule.remoteBranchName}?`}
        visible={this.forcePushModalVisible}
      >
        <b-form on={{ submit: preventDefaultWrapper(this.forcePushToRepo) }}>
          <h4>Warning! You may break something!</h4>
          <p>This will overwrite any changes that were made on the branch:</p>
          <p class="text-bold text-align--center">{SyncProjectRepoPaneStoreModule.remoteBranchName}</p>
          <p>
            The contents of the currently opened project will be forcefully set on this branch. Removing any changes
            that were possibly made by someone else.
          </p>
          <p>To resolve this, push this project to another branch and handle the merge conflict outside of Refinery.</p>

          <div class="display--flex">
            <b-button
              class="mr-1 ml-1 flex-grow--1 width--100percent"
              variant="danger"
              type="submit"
              disabled={SyncProjectRepoPaneStoreModule.isPushingToRepo}
            >
              Confirm Force Push
            </b-button>
          </div>
        </b-form>
      </b-modal>
    );
  }

  public renderCommitButtons() {
    if (SyncProjectRepoPaneStoreModule.getGitPushResult === GitPushResult.UnableToFastForward) {
      return (
        <div class="mt-2">
          <b-button
            variant="danger"
            class="col-12"
            type="submit"
            disabled={SyncProjectRepoPaneStoreModule.isPushingToRepo}
            on={{ click: this.showForcePushModal }}
          >
            Force push
          </b-button>
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

  public async mounted() {
    await SyncProjectRepoPaneStoreModule.diffCompiledProject().then(gitDiff => {
      this.gitDiffInfo = gitDiff;
    });
  }

  public async setRemoteBranchName(branchName: string) {
    await SyncProjectRepoPaneStoreModule.setRemoteBranchName(branchName);
    await SyncProjectRepoPaneStoreModule.clearGitStatusResult();
  }

  public async setNewRemoteBranchName(branchName: string) {
    await SyncProjectRepoPaneStoreModule.setNewRemoteBranchName(branchName);
    await SyncProjectRepoPaneStoreModule.clearGitStatusResult();
  }

  public async runGitShellCommand(command: string) {
    this.gitCommandResult = await SyncProjectRepoPaneStoreModule.runGitCommand(command);
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
    const remoteBranchName = SyncProjectRepoPaneStoreModule.getRemoteBranchName;

    const gitPushProps: LoadingContainerProps = {
      show: SyncProjectRepoPaneStoreModule.isPushingToRepo,
      label: 'Pushing to git repo...'
    };

    return (
      <div class={loadingClasses}>
        <Loading props={gitPushProps}>
          <div>
            <div class="padding--small">
              <label class="d-block">Branch Name:</label>
              <b-form-select
                on={{ input: this.setRemoteBranchName }}
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
                  value={remoteBranchName}
                  on={{ input: this.setNewRemoteBranchName }}
                  placeholder="eg, new-feature"
                />
              </div>
            )}
          </div>

          <b-form-invalid-feedback class="padding--small" state={validBranch}>
            The entered branch name is not valid. Please refer to{' '}
            <a
              href="https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-check-ref-format.html"
              target="_blank"
            >
              check-ref-format
            </a>{' '}
            for valid branch names.
          </b-form-invalid-feedback>

          <hr />

          <label class="d-block">Commit message:</label>
          <b-form-input
            type="text"
            required={true}
            value={SyncProjectRepoPaneStoreModule.commitMessage}
            on={{ input: SyncProjectRepoPaneStoreModule.setCommitMessage }}
            placeholder=""
          />
          {this.renderCommitButtons()}

          <hr />

          <div class="deploy-pane-container__content overflow--scroll-y-auto">{this.renderGitStatusDetails()}</div>

          <hr />

          <b-form-input type="text" on={{ input: this.runGitShellCommand }} />
          <b-textarea value={this.gitCommandResult} />

          {this.renderModal()}
          {this.renderForcePushWarning()}
        </Loading>
      </div>
    );
  }
}
