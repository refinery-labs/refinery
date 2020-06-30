import Vue, { CreateElement, VNode } from 'vue';
import Component, { mixins } from 'vue-class-component';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { isDevelopment, SyncProjectRepoPaneStoreModule as SyncProjectStore } from '@/store';
import { GitPushResult } from '@/store/modules/panes/sync-project-repo-pane';
import { branchNameBlacklistRegex, masterBranchName } from '@/constants/project-editor-constants';
import CreateToastMixin from '@/mixins/CreateToastMixin';
import { Watch } from 'vue-property-decorator';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import Loading from '@/components/Common/Loading.vue';
import { LoadingContainerProps } from '@/types/component-types';

@Component
export default class SyncProjectRepoPane extends mixins(CreateToastMixin) {
  public showingGitStatusDetails: boolean = false;
  public hasToggledNewBranch: boolean = false;
  public forcePushModalVisible: boolean = false;
  public gitCommandResult: string = '';

  @Watch('gitPushResult')
  public async showGitPushErrors() {
    if (!SyncProjectStore.getGitPushResult) {
      return;
    }

    if (SyncProjectStore.getGitPushResult !== GitPushResult.Success) {
      this.displayErrorToast('Git push failure', SyncProjectStore.getGitPushResultMessage);
      return;
    }
    this.displaySuccessToast('Git push success', SyncProjectStore.getGitPushResultMessage);
    await SyncProjectStore.clearGitPushResult();
  }

  @Watch('remoteBranchName')
  public async diffCompiledProject() {
    await SyncProjectStore.clearGitPushResult();

    if (!this.hasToggledNewBranch) {
      try {
        await SyncProjectStore.diffCompiledProjectAndRemoveBranch();
      } catch (e) {
        this.displayErrorToast('Error diffing branch', e.toString());
      }
    } else {
      await SyncProjectStore.checkRemoteBranchName();
    }
  }

  get gitPushResult() {
    return SyncProjectStore.gitPushResult;
  }
  get remoteBranchName() {
    return SyncProjectStore.remoteBranchName;
  }

  public changeCurrentlyDiffedFile(file: string) {
    SyncProjectStore.setCurrentlyDiffedFile(file);
  }

  public getOriginalContent(currentlyDiffedFile: string | null): string {
    if (!currentlyDiffedFile) {
      return '';
    }

    const originalFileContent = SyncProjectStore.gitDiffInfo.originalFiles[currentlyDiffedFile];
    if (!originalFileContent) {
      return '';
    }
    return originalFileContent;
  }

  public getNewContent(currentlyDiffedFile: string | null): string {
    if (!currentlyDiffedFile) {
      return '';
    }

    return SyncProjectStore.gitDiffInfo.changedFiles[currentlyDiffedFile];
  }

  public renderModal() {
    if (!this.showingGitStatusDetails) {
      return null;
    }

    const modalOnHandlers = {
      hidden: () => (this.showingGitStatusDetails = false)
    };

    const diffFiles = Object.keys(SyncProjectStore.gitDiffInfo.changedFiles).map(file => {
      return { value: file, text: file };
    });

    const currentlyDiffedFile = SyncProjectStore.getCurrentlyDiffedFile;

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
    const stats = SyncProjectStore.getGitStatusStats;
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

  public renderGitStatus() {
    if (!SyncProjectStore.creatingNewBranch && SyncProjectStore.gitStatusResult.length > 0) {
      return (
        <div>
          <hr />

          <div class="deploy-pane-container__content overflow--scroll-y-auto">{this.renderGitStatusDetails()}</div>
        </div>
      );
    }
    return null;
  }

  public async forcePushToRepo() {
    await SyncProjectStore.forcePushToRemoteBranch();
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
        title={`Force push to the branch ${SyncProjectStore.remoteBranchName}?`}
        visible={this.forcePushModalVisible}
      >
        <b-form on={{ submit: preventDefaultWrapper(this.forcePushToRepo) }}>
          <h4>Warning! You may break something!</h4>
          <p>This will overwrite any changes that were made on the branch:</p>
          <p class="text-bold text-align--center">{SyncProjectStore.remoteBranchName}</p>
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
              disabled={SyncProjectStore.isPushingToRepo}
            >
              Confirm Force Push
            </b-button>
          </div>
        </b-form>
      </b-modal>
    );
  }

  public renderCommitButtons() {
    if (SyncProjectStore.getGitPushResult === GitPushResult.UnableToFastForward) {
      return (
        <div class="mt-2">
          <b-button
            variant="danger"
            class="col-12"
            type="submit"
            disabled={SyncProjectStore.isPushingToRepo}
            on={{ click: this.showForcePushModal }}
          >
            Force push
          </b-button>
          <div class="padding-left--normal padding-right--normal">
            <small>To avoid a force push, 'Create a new branch' and push your changes to this new branch.</small>
          </div>
        </div>
      );
    }

    return (
      <div class="mt-2">
        <b-button
          variant="primary"
          class="col-12"
          type="submit"
          disabled={SyncProjectStore.isPushingToRepo || SyncProjectStore.isDiffingBranch}
          on={{ click: SyncProjectStore.pushToRemoteBranch }}
        >
          Push to branch
        </b-button>
      </div>
    );
  }

  public async mounted() {
    await SyncProjectStore.diffCompiledProjectAndRemoveBranch();
  }

  public setRemoteBranchName(branchName: string) {
    if (SyncProjectStore.creatingNewBranch) {
      return;
    }

    SyncProjectStore.setRemoteBranchName(branchName);
    SyncProjectStore.clearGitStatusResult();
  }

  public setNewRemoteBranchName(branchName: string) {
    SyncProjectStore.setNewRemoteBranchName(branchName);
    SyncProjectStore.clearGitStatusResult();
  }

  public async runGitShellCommand(command: string) {
    this.gitCommandResult = await SyncProjectStore.runGitCommand(command);
  }

  public setCreatingNewBranch(creatingNewBranch: boolean) {
    if (creatingNewBranch && !this.hasToggledNewBranch) {
      SyncProjectStore.setRandomRemoteBranchName();
      this.hasToggledNewBranch = true;
    }
    if (!creatingNewBranch) {
      this.hasToggledNewBranch = false;
    }
    SyncProjectStore.setCreatingNewBranch(creatingNewBranch);
  }

  public getFirstBranchName() {
    const repoBranches = SyncProjectStore.repoBranches;

    if (repoBranches.includes(SyncProjectStore.remoteBranchName)) {
      return SyncProjectStore.remoteBranchName;
    }

    if (repoBranches.includes(masterBranchName)) {
      return masterBranchName;
    }
    return repoBranches[0];
  }

  public async clickExistingBranchCard() {
    await this.setCreatingNewBranch(false);

    const firstBranch = this.getFirstBranchName();
    this.setRemoteBranchName(firstBranch);
  }

  public showDevelopmentGitShell() {
    return (
      <div>
        <h4>Git Shell</h4>
        <p>Project Session ID: {SyncProjectStore.projectSessionId}</p>
        <b-form-input type="text" placeholder="command" on={{ input: this.runGitShellCommand }} />
        <b-textarea placeholder="output" class="margin-top--small" value={this.gitCommandResult} />
      </div>
    );
  }

  public renderSelectExistingBranchCard() {
    const repoBranches = SyncProjectStore.repoBranches;

    if (repoBranches.length === 0) {
      return null;
    }

    const selectRepoBranches = repoBranches.map(branch => {
      return { value: branch, text: branch };
    });
    const branchName = this.getFirstBranchName();

    return (
      <b-card
        no-body
        bg-variant={!SyncProjectStore.creatingNewBranch ? 'light' : 'default'}
        on={{ click: this.clickExistingBranchCard }}
      >
        <b-card-header header-tag="header" className="p-1" role="tab">
          <h5>Use existing branch</h5>
        </b-card-header>
        <b-collapse
          id="existing-branch-collapse"
          visible={!SyncProjectStore.creatingNewBranch}
          accordion="repo-branch-accordion"
          role="tabpanel"
        >
          <b-card-body>
            <b-form-select on={{ input: this.setRemoteBranchName }} value={branchName} options={selectRepoBranches} />
          </b-card-body>
        </b-collapse>
      </b-card>
    );
  }

  public renderCreateNewBranchCard() {
    const remoteBranchName = SyncProjectStore.getRemoteBranchName;

    const repoBranches = SyncProjectStore.repoBranches;
    const visible = repoBranches.length === 0 || SyncProjectStore.creatingNewBranch;

    return (
      <b-card
        no-body
        className="mb-1"
        bg-variant={visible ? 'light' : 'default'}
        on={{ click: async () => await this.setCreatingNewBranch(true) }}
      >
        <b-card-header header-tag="header" className="p-1" role="tab">
          <h5>Create a new branch</h5>
        </b-card-header>
        <b-collapse id="new-branch-collapse" visible={visible} accordion="repo-branch-accordion" role="tabpanel">
          <b-card-body>
            <b-form-input
              type="text"
              autofocus={true}
              required={true}
              state={SyncProjectStore.isValidRemoteBranchName}
              value={remoteBranchName}
              on={{ input: this.setNewRemoteBranchName }}
              placeholder="eg, new-feature"
            />
            <b-form-invalid-feedback className="padding--small" state={SyncProjectStore.isValidRemoteBranchName}>
              The entered branch name is not valid. Please refer to{' '}
              <a
                href="https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-check-ref-format.html"
                target="_blank"
              >
                check-ref-format
              </a>{' '}
              for valid branch names.
            </b-form-invalid-feedback>
          </b-card-body>
        </b-collapse>
      </b-card>
    );
  }

  public renderRepoBranchSelect() {
    const gitBranchProps: LoadingContainerProps = {
      show: SyncProjectStore.isDiffingBranch,
      label: 'Diffing branch...'
    };
    return (
      <div>
        <Loading props={gitBranchProps}>
          <label class="d-block">Branch Name:</label>
          <div role="tablist" class="set-project-repo">
            {this.renderSelectExistingBranchCard()}
            {this.renderCreateNewBranchCard()}
          </div>
        </Loading>
      </div>
    );
  }

  public renderDevelopmentShell() {
    if (isDevelopment) {
      return (
        <div>
          <hr />
          {this.showDevelopmentGitShell()}
        </div>
      );
    }
    return null;
  }

  public render(h: CreateElement): VNode {
    const loadingClasses = {
      'whirl standard': !SyncProjectStore.gitStatusResult,
      'text-align--left': true,
      'padding--normal': true,
      'sync-project-repo-container': true
    };

    const gitPushProps: LoadingContainerProps = {
      show: SyncProjectStore.isPushingToRepo,
      label: 'Pushing to git repo...'
    };

    return (
      <div class={loadingClasses}>
        <Loading props={gitPushProps}>
          {this.renderRepoBranchSelect()}

          <label class="d-block">Commit message:</label>
          <b-form-input
            type="text"
            required={true}
            value={SyncProjectStore.commitMessage}
            on={{ input: SyncProjectStore.setCommitMessage }}
            placeholder=""
          />
          {this.renderCommitButtons()}

          {this.renderGitStatus()}

          {this.renderDevelopmentShell()}

          {this.renderModal()}
          {this.renderForcePushWarning()}
        </Loading>
      </div>
    );
  }
}
