import { VNode } from 'vue';
import Component, { mixins } from 'vue-class-component';
import { namespace, State } from 'vuex-class';
import ImportableRefineryProject from '@/types/export-project';
import { Route } from 'vue-router';
import store, { UnauthViewProjectStoreModule } from '@/store';
import { DeploymentViewMutators, ProjectViewActions, ProjectViewMutators } from '@/constants/store-constants';
import OpenedProjectOverview from '@/views/ProjectsNestedViews/OpenedProjectOverview';
import SignupModal, { SignupModalProps } from '@/components/Demo/SignupModal';
import CreateToastMixin from '@/mixins/CreateToastMixin';
import { ImportProjectType } from '@/store/store-types';
import DeployFromGithub from '@/components/Signup/DeployFromGithub';

import('../monaco-shims');

const allProjects = namespace('allProjects');
const project = namespace('project');

@Component
export default class ImportProject extends mixins(CreateToastMixin) {
  @allProjects.State importProjectType!: ImportProjectType | null;
  @allProjects.State importProjectFromUrlContent!: string | null;
  @allProjects.State importProjectFromUrlError!: string | null;
  @allProjects.State importProjectFromUrlBusy!: boolean;

  @project.State selectedResourceDirty!: boolean;

  @allProjects.Getter importProjectFromUrlValid!: boolean;
  @allProjects.Getter importProjectFromUrlJson!: ImportableRefineryProject | null;

  @project.Getter canSaveProject!: boolean;

  @allProjects.Mutation setImportProjectFromUrlContent!: (val: string) => void;

  @allProjects.Action importProjectFromDemo!: () => void;

  @State windowWidth?: number;

  // Insert the Demo JSON into the store.
  public async beforeRouteEnter(to: Route, from: Route, next: () => void) {
    store.dispatch(`user/fetchAuthenticationState`);

    // Don't await so that we can have the UI pop up faster.
    store.dispatch(`project/${ProjectViewActions.openDemo}`);

    next();
  }

  public beforeRouteLeave(to: Route, from: Route, next: () => void) {
    if (this.canSaveProject || this.selectedResourceDirty) {
      this.displayErrorToast('Unable to Navigate', 'Please save the current project or resource before continuing.');
      return;
    }

    next();
    store.commit(`project/${ProjectViewMutators.resetState}`);
    store.commit(`deployment/${DeploymentViewMutators.resetState}`);
  }

  renderUnauthGraph() {
    const classes = {
      'graph-visibility': true,

      'graph-with-grid': true,
      'flex-grow--1': true,
      'display--flex': true
    };

    return (
      <div class={classes}>
        <OpenedProjectOverview />;
      </div>
    );
  }

  public renderContents(): VNode {
    const exampleProjectButton = (
      <div class="padding-top--normal">
        <b-button variant="primary" href="https://docs.refinery.io/tutorials/scraping-a-million-urls/" target="_blank">
          View Example Projects
        </b-button>
      </div>
    );

    if (this.importProjectFromUrlBusy) {
      return (
        <div class="unauth-graph-container padding-top--huge">
          <h2>Loading project... One moment, please!</h2>
          <div class="padding-top--normal">
            <b-spinner />
          </div>
        </div>
      );
    }

    const exampleProjectText = <h3>For some example projects to check out, please check out our tutorials below!</h3>;

    if (this.importProjectFromUrlError) {
      return (
        <div class="unauth-graph-container">
          <h2>Error: {this.importProjectFromUrlError}</h2>
          {exampleProjectText}
          {exampleProjectButton}
        </div>
      );
    }

    if (!this.importProjectFromUrlValid) {
      return (
        <div class="unauth-graph-container">
          <h2>Invalid project to import.</h2>
          {exampleProjectText}
          {exampleProjectButton}
        </div>
      );
    }

    return <div>{this.renderUnauthGraph()}</div>;
  }

  public getImportView() {
    if (this.importProjectType === ImportProjectType.URL) {
      const signupModalProps: SignupModalProps = {
        showModal: UnauthViewProjectStoreModule.showSignupModal,
        isModal: true,
        closeModal: () => UnauthViewProjectStoreModule.setShowSignupModal(false)
      };

      return (
        <div>
          <b-nav tabs justified>
            <b-nav-item exact active-nav-item-class="active" data-tooltip-id="editor-nav-item">
              Editor
            </b-nav-item>
            <b-nav-item>Deployment</b-nav-item>
            <b-nav-item>Settings</b-nav-item>
          </b-nav>
          <div class="view-project-page-content position--relative flex-grow--1 width--100percent height--100percent">
            {this.renderContents()}
            <SignupModal props={signupModalProps} />
          </div>
        </div>
      );
    } else if (this.importProjectType === ImportProjectType.REPO) {
      return <DeployFromGithub />;
    }
    return null;
  }

  public render() {
    if (this.importProjectType === null) {
      return null;
    }

    return <div class="view-project-page">{this.getImportView()}</div>;
  }
}
