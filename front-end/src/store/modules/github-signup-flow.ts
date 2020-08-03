import { Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { createNewProjectFromConfig } from '@/utils/new-project-utils';
import { AllProjectsMutators, ProjectViewActions } from '@/constants/store-constants';
import slugify from 'slugify';
import { RepoManagerStoreModule } from '@/store';
import { DeployFromGithubStateType } from '@/types/github-signup-flow-types';
import { LoggingAction } from '@/lib/LoggingMutation';
import { OpenProjectMutation } from '@/types/project-editor-types';

// This is the name that this will be added to the Vuex store with.
// You will need to add to the `RootState` interface if you want to access this state via `rootState` from anywhere.
const storeName = StoreType.githubSignupFlow;

export interface GithubSignupFlowState {
  deployFromGithubState: DeployFromGithubStateType;
}

export const baseState: GithubSignupFlowState = {
  deployFromGithubState: DeployFromGithubStateType.NOT_STARTED
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: storeName })
export class GithubSignupFlowStore extends VuexModule<ThisType<GithubSignupFlowState>, RootState>
  implements GithubSignupFlowState {
  public deployFromGithubState: DeployFromGithubStateType = baseState.deployFromGithubState;

  get isCompilingProjectFromGithub(): boolean {
    return this.deployFromGithubState === DeployFromGithubStateType.COMPILING_PROJECT_FROM_GITHUB;
  }

  get isConnectingToGithub(): boolean {
    return this.deployFromGithubState === DeployFromGithubStateType.WAITING_FOR_GITHUB_AUTH;
  }

  get isWaitingForGithubResponse(): boolean {
    return this.deployFromGithubState === DeployFromGithubStateType.WAITING_FOR_GITHUB_RESPONSE;
  }

  get isPushingToGithubRepo(): boolean {
    return this.deployFromGithubState === DeployFromGithubStateType.PUSHING_PROJECT_TO_GITHUB_REPO;
  }

  get isCreatingNewRepo(): boolean {
    return this.deployFromGithubState === DeployFromGithubStateType.CHOOSING_GITHUB_REPO;
  }

  get isDeployingOnRefinery(): boolean {
    return this.deployFromGithubState === DeployFromGithubStateType.PROJECT_PUSHED_TO_GITHUB_REPO;
  }

  @Mutation
  public setGithubSignupState(githubSignupState: DeployFromGithubStateType) {
    this.deployFromGithubState = githubSignupState;
  }

  @LoggingAction
  public async createNewProject() {
    const openedProject = this.context.rootState.project.openedProject;
    if (!openedProject) {
      throw Error('There is no currently opened project');
    }

    const projectName = openedProject.name;

    const projectId = await createNewProjectFromConfig({
      setStatus: status =>
        this.context.commit(`allProjects/${AllProjectsMutators.setNewProjectBusy}`, status, { root: true }),
      setError: (message: string | null) =>
        this.context.commit(`allProjects/${AllProjectsMutators.setNewProjectErrorMessage}`, message, { root: true }),
      unknownError: 'Error creating project!',
      navigateToNewProject: false,
      name: projectName,
      json: JSON.stringify(openedProject)
    });

    if (projectId === null) {
      throw Error();
    }

    const modifiedProject = {
      ...openedProject,
      project_id: projectId
    };

    const params: OpenProjectMutation = {
      project: modifiedProject,
      config: this.context.rootState.project.openedProjectConfig,
      markAsDirty: false
    };
    await this.context.dispatch(`project/${ProjectViewActions.updateProject}`, params, { root: true });
  }
}
