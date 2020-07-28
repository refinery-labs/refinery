import Component from 'vue-class-component';
import Vue from 'vue';
import { namespace } from 'vuex-class';
import RepoSelector, { RepoSelectorProps } from '@/components/ProjectSettings/RepoSelector';
import { GithubSignupFlowStoreModule, RepoManagerStoreModule } from '@/store';
import { DeployFromGithubStateType } from '@/types/github-signup-flow-types';
import { RefineryProject } from '@/types/graph';
import slugify from 'slugify';
import Loading from '@/components/Common/Loading.vue';
import { LoadingContainerProps } from '@/types/component-types';
import { viewProject } from '@/utils/router-utils';

const project = namespace('project');
const user = namespace('user');

@Component
export default class DeployFromGithub extends Vue {
  @project.State openedProject!: RefineryProject | null;

  @user.Action authWithGithub!: () => void;

  private async selectedRepoCallback() {
    GithubSignupFlowStoreModule.setGithubSignupState(DeployFromGithubStateType.PUSHING_PROJECT_TO_GITHUB_REPO);

    await RepoManagerStoreModule.pushToRepo(false);

    GithubSignupFlowStoreModule.setGithubSignupState(DeployFromGithubStateType.PROJECT_PUSHED_TO_GITHUB_REPO);
  }

  private closeAndDeploy() {
    if (!this.openedProject) {
      throw Error();
    }
    viewProject(this.openedProject.project_id);
  }

  private render() {
    if (GithubSignupFlowStoreModule.isCompilingProjectFromGithub) {
      return <p>Importing project from Github please wait...</p>;
    }

    if (!this.openedProject) {
      return <p>Unable to import project to deploy on Refinery!</p>;
    }

    const projectRepoName = slugify(this.openedProject.name);

    const repoSelectorProps: RepoSelectorProps = {
      selectedRepoCallback: this.selectedRepoCallback,
      showClearRepoButton: false
    };

    const connectToGithubLoadingProps: LoadingContainerProps = {
      show: GithubSignupFlowStoreModule.isWaitingForGithubResponse,
      label: 'Waiting for Github authentication...'
    };

    const selectRepoLoadingProps: LoadingContainerProps = {
      show: GithubSignupFlowStoreModule.isPushingToGithubRepo,
      label: 'Pushing project to new repo...'
    };

    const connectToGithubTabShowing =
      GithubSignupFlowStoreModule.isConnectingToGithub || GithubSignupFlowStoreModule.isWaitingForGithubResponse;
    const selectProjectRepoTabShowing =
      GithubSignupFlowStoreModule.isCreatingNewRepo || GithubSignupFlowStoreModule.isPushingToGithubRepo;
    const deployTabShowing = GithubSignupFlowStoreModule.isDeployingOnRefinery;

    const shouldBoldFont = (active: boolean) => (active ? 'font-weight: bold' : '');

    return (
      <div style="margin-left: auto; margin-right: auto; width:800px; margin-top: 200px">
        <h3>Deploy your code on Refinery in a minute!</h3>
        <div style="margin-top: 25px">
          <div style="font-size: large">
            <label style={shouldBoldFont(connectToGithubTabShowing)}>Signup</label> -{' '}
            <label style={shouldBoldFont(selectProjectRepoTabShowing)}>Save</label> -{' '}
            <label style={shouldBoldFont(deployTabShowing)}>Deploy</label>
          </div>
          <b-card-group>
            <b-card
              style="max-width: 20rem;"
              className="mb-2"
              title="Create a free account"
              hidden={!connectToGithubTabShowing}
            >
              <Loading props={connectToGithubLoadingProps}>
                <b-card-text>
                  Connect Refinery to Github in order to create the <code>{projectRepoName}</code> repository in your
                  account.
                </b-card-text>
                <b-button on={{ click: this.authWithGithub }} variant="primary">
                  Connect to Github
                </b-button>
              </Loading>
            </b-card>
            <b-card style="max-width: 20rem;" className="mb-2" hidden={!selectProjectRepoTabShowing}>
              <h4 style="card-title">
                Save <code>{projectRepoName}</code> to a repository.
              </h4>
              <Loading props={selectRepoLoadingProps}>
                <RepoSelector props={repoSelectorProps} />
              </Loading>
            </b-card>
            <b-card style="max-width: 20rem;" className="mb-2" hidden={!deployTabShowing}>
              <b-card-text>You account has been all setup and you are now ready to deploy!</b-card-text>
              <b-button variant="primary" on={{ click: this.closeAndDeploy }}>
                Deploy
              </b-button>
            </b-card>
          </b-card-group>
        </div>
      </div>
    );
  }
}
