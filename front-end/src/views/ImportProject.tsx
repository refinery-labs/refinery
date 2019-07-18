import Vue, { VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import ImportableRefineryProject from '@/types/export-project';

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

  mounted() {
    // this.setImportProjectFromUrlContent(window.location.hash);
  }

  public renderContent(): VNode {
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

    return (
      <div class="import-project-page">
        <h2>
          Are you sure would like to import <i>{this.importProjectFromUrlJson.name}</i>?
        </h2>
        <div class="padding-top--normal">
          <b-button variant="primary" on={{ click: this.importProjectByUrlHash }}>
            Import <i>{this.importProjectFromUrlJson.name}</i>
          </b-button>
        </div>
      </div>
    );
  }

  public render() {
    return (
      <div class="text-align--center">
        <div class="margin-left--auto margin-right--auto padding-top--huge" style="max-width: 500px">
          {this.renderContent()}
        </div>
      </div>
    );
  }
}
