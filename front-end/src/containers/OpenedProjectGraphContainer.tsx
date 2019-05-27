import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import CytoscapeGraph from '@/components/CytoscapeGraph';
import {
  namespace
} from 'vuex-class'
import {
  BaseRefineryResource,
  CyElements,
  CyStyle,
  RefineryProject,
  WorkflowRelationship,
  WorkflowState
} from '@/types/graph';
import {LayoutOptions} from 'cytoscape';
import {Watch} from 'vue-property-decorator';
import {Route} from 'vue-router';
import {GetSavedProjectRequest} from '@/types/api-types';

const project = namespace('project');

@Component
export default class OpenedProjectGraphContainer extends Vue {
  @project.State openedProject!: RefineryProject | null;
  @project.State selectedResource!: BaseRefineryResource | null;
  @project.State cytoscapeElements!: CyElements | null;
  @project.State cytoscapeStyle!: CyStyle | null;
  @project.State cytoscapeLayoutOptions!: LayoutOptions | null;
  @project.State cytoscapeConfig!: cytoscape.CytoscapeOptions | null;
  
  @project.Action selectNode!: (element: WorkflowState) => {};
  @project.Action selectEdge!: (element: WorkflowRelationship) => {};
  
  public render(h: CreateElement): VNode {
    
    if (!this.cytoscapeElements || !this.cytoscapeStyle) {
      const errorMessage = 'Graph unable to render, missing data!';
      console.error(errorMessage);
      return (
        <h2>{errorMessage}</h2>
      );
    }
   
    // By holding these in the stores, we can compare pointers because the data is "immutable".
    const graphProps = {
      selectNode: this.selectNode,
      selectEdge: this.selectEdge,
      elements: this.cytoscapeElements,
      stylesheet: this.cytoscapeStyle,
      layout: this.cytoscapeLayoutOptions,
      config: this.cytoscapeConfig,
      selected: this.selectedResource && this.selectedResource.id
    };
    
    return (
      <div class="opened-project-graph-container flex-grow--1">
        <CytoscapeGraph props={graphProps} />
      </div>
    );
  }
}
