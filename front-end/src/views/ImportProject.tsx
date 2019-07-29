import Vue, { VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace, State } from 'vuex-class';
import ImportableRefineryProject from '@/types/export-project';
import { Route } from 'vue-router';
import store from '@/store';
import { ProjectViewActions } from '@/constants/store-constants';
import OpenedProjectOverview from '@/views/ProjectsNestedViews/OpenedProjectOverview';
import { UnauthViewProjectStoreModule } from '@/store/modules/unauth-view-project';
import SignupModal, { SignupModalProps } from '@/components/Demo/SignupModal';

const allProjects = namespace('allProjects');

@Component
export default class ImportProject extends Vue {
  @allProjects.State importProjectFromUrlContent!: string | null;
  @allProjects.State importProjectFromUrlError!: string | null;
  @allProjects.State importProjectBusy!: boolean;

  @allProjects.Getter importProjectFromUrlValid!: boolean;
  @allProjects.Getter importProjectFromUrlJson!: ImportableRefineryProject | null;

  @allProjects.Mutation setImportProjectFromUrlContent!: (val: string) => void;

  @allProjects.Action importProjectByUrlHash!: () => void;

  @State windowWidth?: number;

  // Insert the Demo JSON into the store.
  public async beforeRouteEnter(to: Route, from: Route, next: () => void) {
    await store.dispatch(`project/${ProjectViewActions.openDemo}`);

    next();
  }

  renderUnauthGraph() {
    return <OpenedProjectOverview />;
  }

  public renderContents(): VNode {
    const exampleProjectButton = (
      <div class="padding-top--normal">
        <b-button variant="primary" href="https://docs.refinery.io/tutorials/scraping-a-million-urls/" target="_blank">
          View Example Projects
        </b-button>
      </div>
    );

    const exampleProjectText = <h3>For some example projects to check out, please check out our tutorials below!</h3>;

    if (!this.importProjectFromUrlContent) {
      return (
        <div class="import-project-page">
          <h2>Unable to locate project to import.</h2>
          {exampleProjectText}
          {exampleProjectButton}
        </div>
      );
    }

    if (!this.importProjectFromUrlValid) {
      return (
        <div class="import-project-page">
          <h2>Invalid project to import.</h2>
          {exampleProjectText}
          {exampleProjectButton}
        </div>
      );
    }

    if (this.importProjectFromUrlError || !this.importProjectFromUrlJson) {
      return (
        <div class="import-project-page">
          <h2>Error Importing Project.</h2>
          {exampleProjectText}
          {exampleProjectButton}
          <h5>{this.importProjectFromUrlError}</h5>
        </div>
      );
    }

    if (this.importProjectBusy) {
      return (
        <div class="import-project-page">
          <h2>Importing project... You will be redirected in a moment.</h2>
          <div class="padding-top--normal">
            <b-spinner />
          </div>
        </div>
      );
    }

    return <div class="unauth-graph-container">{this.renderUnauthGraph()}</div>;
  }

  public render() {
    const signupModalProps: SignupModalProps = {
      showModal: UnauthViewProjectStoreModule.showSignupModal,
      isModal: true,
      closeModal: () => UnauthViewProjectStoreModule.setShowSignupModal(false)
    };

    return (
      <div>
        {this.renderContents()}
        <SignupModal props={signupModalProps} />
      </div>
    );
  }
}
