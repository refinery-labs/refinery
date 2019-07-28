import Vue, { VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace, State } from 'vuex-class';
import ImportableRefineryProject from '@/types/export-project';
import { UnauthViewProjectStoreModule } from '@/store/modules/unauth-view-project';
import CytoscapeGraph from '@/components/CytoscapeGraph';
import { CytoscapeGraphProps } from '@/types/cytoscape-types';
import { WorkflowRelationship, WorkflowRelationshipType, WorkflowState } from '@/types/graph';

const allProjects = namespace('allProjects');

@Component
export default class ViewUnauthProject extends Vue {
  @allProjects.State importProjectFromUrlContent!: string | null;
  @allProjects.State importProjectFromUrlError!: string | null;
  @allProjects.State importProjectBusy!: boolean;

  @allProjects.Getter importProjectFromUrlValid!: boolean;
  @allProjects.Getter importProjectFromUrlJson!: ImportableRefineryProject | null;

  @allProjects.Mutation setImportProjectFromUrlContent!: (val: string) => void;

  @allProjects.Action importProjectByUrlHash!: () => void;

  @State windowWidth?: number;

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

  renderUnauthGraph() {
    const style = UnauthViewProjectStoreModule.cytoscapeStyle;
    const elements = UnauthViewProjectStoreModule.cytoscapeElements;

    if (!style || !elements) {
      return <div>No elements loaded</div>;
    }

    const graphProps: CytoscapeGraphProps = {
      clearSelection: () => UnauthViewProjectStoreModule.setSelectedElement(null),
      selectNode: (element: WorkflowState) => UnauthViewProjectStoreModule.setSelectedElement(element.id),
      selectEdge: (element: WorkflowRelationship) => UnauthViewProjectStoreModule.setSelectedElement(element.id),
      elements: elements,
      stylesheet: style,
      layout: null,
      config: null,
      selected: UnauthViewProjectStoreModule.selectedElement,
      enabledNodeIds: null,
      backgroundGrid: true,
      windowWidth: this.windowWidth
    };

    return <CytoscapeGraph props={graphProps} />;
  }

  public render() {
    return <div class="unauth-graph-container">{this.renderUnauthGraph()}</div>;
  }
}
