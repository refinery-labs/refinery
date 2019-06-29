import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import CytoscapeGraph from '@/components/CytoscapeGraph';
import { namespace, State } from 'vuex-class';
import { RefineryProject, WorkflowRelationship, WorkflowState } from '@/types/graph';
import { LayoutOptions } from 'cytoscape';
import { AvailableTransition } from '@/store/store-types';
import { CyElements, CyStyle, CytoscapeGraphProps } from '@/types/cytoscape-types';

const deployment = namespace('deployment');
const deploymentExecutions = namespace('deploymentExecutions');

@Component
export default class DeploymentViewerGraphContainer extends Vue {
  @deployment.State selectedResource!: string | null;
  @deployment.State cytoscapeElements!: CyElements | null;
  @deployment.State cytoscapeStyle!: CyStyle | null;
  @deployment.State cytoscapeLayoutOptions!: LayoutOptions | null;
  @deployment.State cytoscapeConfig!: cytoscape.CytoscapeOptions | null;

  @deployment.State isLoadingDeployment!: boolean;
  @State windowWidth?: number;

  @deploymentExecutions.Getter graphElementsWithExecutionStatus!: CyElements | null;

  @deployment.Action clearSelection!: () => {};
  @deployment.Action selectNode!: (element: WorkflowState) => {};
  @deployment.Action selectEdge!: (element: WorkflowRelationship) => {};

  public render(h: CreateElement): VNode {
    if (this.isLoadingDeployment) {
      return <h2>Waiting for data...</h2>;
    }

    if (!this.cytoscapeElements || !this.cytoscapeStyle) {
      const errorMessage = 'Graph unable to render, missing data!';
      console.error(errorMessage);
      return <h2>{errorMessage}</h2>;
    }

    // By holding these in the stores, we can compare pointers because the data is "immutable".
    const graphProps: CytoscapeGraphProps = {
      clearSelection: this.clearSelection,
      selectNode: this.selectNode,
      selectEdge: this.selectEdge,
      elements: this.graphElementsWithExecutionStatus || this.cytoscapeElements,
      stylesheet: this.cytoscapeStyle,
      layout: this.cytoscapeLayoutOptions,
      config: this.cytoscapeConfig,
      selected: this.selectedResource,
      enabledNodeIds: null,
      backgroundGrid: false,
      windowWidth: this.windowWidth
    };

    return (
      <div class="deployment-viewer-graph-container flex-grow--1">
        <CytoscapeGraph props={graphProps} />
      </div>
    );
  }
}
