import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace, State } from 'vuex-class';
import { LayoutOptions } from 'cytoscape';
import CytoscapeGraph from '@/components/CytoscapeGraph';
import { CyElements, CyStyle, CytoscapeGraphProps } from '@/types/cytoscape-types';
import { DemoWalkthroughStoreModule } from '@/store';
import Tooltip from '@/lib/Tooltip';
import { TooltipType } from '@/types/demo-walkthrough-types';
import { TooltipProps } from '@/types/tooltip-types';

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

  public getDemoWalkthrough() {
    const tooltipProps: TooltipProps = {
      step: DemoWalkthroughStoreModule.currentHTMLTooltip,
      nextTooltip: DemoWalkthroughStoreModule.nextTooltip,
      skipTooltips: DemoWalkthroughStoreModule.skipWalkthrough
    };

    if (DemoWalkthroughStoreModule.currentHTMLTooltip) {
      return (
        <div>
          <Tooltip props={tooltipProps} />
        </div>
      );
    }
    return <div />;
  }

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
      currentTooltips: DemoWalkthroughStoreModule.cyTooltips,
      loadCyTooltips: DemoWalkthroughStoreModule.loadCyTooltips,
      nextTooltip: DemoWalkthroughStoreModule.nextTooltip,
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

    const demoWalkthrough = this.getDemoWalkthrough();

    return (
      <div class="deployment-viewer-graph-container project-graph-container">
        {demoWalkthrough}
        <CytoscapeGraph props={graphProps} />
      </div>
    );
  }
}
