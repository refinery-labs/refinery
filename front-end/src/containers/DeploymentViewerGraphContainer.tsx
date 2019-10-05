import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import CytoscapeGraph from '@/components/CytoscapeGraph';
import { namespace, State } from 'vuex-class';
import { LayoutOptions } from 'cytoscape';
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

  @State windowWidth?: number;

  @deploymentExecutions.Getter graphElementsWithExecutionStatus!: CyElements | null;

  @deployment.Action clearSelection!: () => void;
  @deployment.Action selectNode!: (element: string) => void;
  @deployment.Action selectEdge!: (element: string) => void;

  public render(h: CreateElement): VNode {
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
      windowWidth: this.windowWidth,
      // Looks janky in the deployment view when you tab back-and-forth
      animationDisabled: true
    };

    return (
      <div class="deployment-viewer-graph-container project-graph-container">
        <CytoscapeGraph props={graphProps} />
      </div>
    );
  }
}
