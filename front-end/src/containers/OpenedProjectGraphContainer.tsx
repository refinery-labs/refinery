import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import CytoscapeGraph from '@/components/CytoscapeGraph';
import { namespace, State } from 'vuex-class';
import { RefineryProject, WorkflowRelationship, WorkflowState } from '@/types/graph';
import { LayoutOptions } from 'cytoscape';
import { AvailableTransition } from '@/store/store-types';
import { CyElements, CyStyle, CytoscapeGraphProps } from '@/types/cytoscape-types';

const project = namespace('project');

@Component
export default class OpenedProjectGraphContainer extends Vue {
  @project.State openedProject!: RefineryProject | null;
  @project.State selectedResource!: string | null;
  @project.State cytoscapeElements!: CyElements | null;
  @project.State cytoscapeStyle!: CyStyle | null;
  @project.State cytoscapeLayoutOptions!: LayoutOptions | null;
  @project.State cytoscapeConfig!: cytoscape.CytoscapeOptions | null;

  @project.State isLoadingProject!: boolean;
  @project.State isInDemoMode!: boolean;
  @State windowWidth?: number;

  @project.Getter getValidBlockToBlockTransitions!: AvailableTransition[] | null;

  @project.Action clearSelection!: () => void;
  @project.Action selectNode!: (element: string) => void;
  @project.Action selectEdge!: (element: string) => void;

  public getEnabledNodeIds() {
    if (!this.getValidBlockToBlockTransitions) {
      return null;
    }

    return this.getValidBlockToBlockTransitions.map(v => v.toNode.id);
  }

  public render(h: CreateElement): VNode {
    if (this.isLoadingProject) {
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
      elements: this.cytoscapeElements,
      stylesheet: this.cytoscapeStyle,
      layout: this.cytoscapeLayoutOptions,
      config: this.cytoscapeConfig,
      selected: this.selectedResource,
      enabledNodeIds: this.getEnabledNodeIds(),
      backgroundGrid: true,
      windowWidth: this.windowWidth
    };

    return (
      <div class="opened-project-graph-container project-graph-container">
        <div class="opened-project-graph-container__project-name">
          <h4>
            <i>
              {this.isInDemoMode ? 'Importing: ' : ''}
              {this.openedProject && this.openedProject.name}
            </i>
          </h4>
        </div>
        <CytoscapeGraph props={graphProps} />
      </div>
    );
  }
}
