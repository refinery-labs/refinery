import {CreateElement, VNode} from 'vue';
import {Component, Prop, Vue, Watch} from 'vue-property-decorator';
import cytoscape, {EventObject, LayoutOptions, NodeCollection} from 'cytoscape';
import dagre from 'cytoscape-dagre';
import {CyElements, CyStyle, WorkflowRelationship, WorkflowState} from '@/types/graph';
import {baseCytoscapeStyles, STYLE_CLASSES} from '@/lib/cytoscape-styles';


cytoscape.use(dagre);

@Component
export default class CytoscapeGraph extends Vue {
  cy!: cytoscape.Core;
  
  @Prop({required: true}) private elements!: CyElements;
  @Prop() private layout!: LayoutOptions;
  @Prop({required: true}) private stylesheet!: CyStyle;
  
  @Prop({required: true}) private selectNode!: (element: WorkflowState) => {};
  @Prop({required: true}) private selectEdge!: (element: WorkflowRelationship) => {};
  @Prop() private selected!: string;
  
  // This is a catch-all for any additional options that need to be specified
  @Prop({default: () => {}}) private config!: cytoscape.CytoscapeOptions;
  
  public cytoscapeValueModified() {
    if (!this.cy) {
      // TODO: Make this development only?
      console.error('Graph not loaded yet and elements were modified!');
      return;
    }
  
    // Tells the Cytoscape graph to update. The library internally diffs elements based on their ID.
    this.cy.json(this.generateInitialCytoscapeConfig());
    
    // Re-select the node on the graph
    this.selectNodeOrEdgeInInstance(this.cy.elements(`#${this.selected}`));
  }
  
  @Watch('elements', {deep: true})
  private elementsModified(val: CyElements, oldVal: CyElements) {
    if (val === oldVal) {
      return;
    }
    
    this.cytoscapeValueModified();
  }
  
  @Watch('layout', {deep: true})
  private layoutModified(val: LayoutOptions, oldVal: LayoutOptions) {
    if (val === oldVal) {
      return;
    }
  
    this.cytoscapeValueModified();
  }
  
  @Watch('stylesheet', {deep: true})
  private styleModified(val: CyStyle, oldVal: CyStyle) {
    if (val === oldVal) {
      return;
    }
  
    this.cytoscapeValueModified();
  }
  
  @Watch('config', {deep: true})
  private configModified(val: cytoscape.CytoscapeOptions, oldVal: cytoscape.CytoscapeOptions) {
    if (val === oldVal) {
      return;
    }
  
    this.cytoscapeValueModified();
  }
  
  @Watch('selected')
  private selectedModified(val: string, oldVal: string) {
    if (val === oldVal || !this.cy) {
      return;
    }
    
    this.selectNodeOrEdgeInInstance(this.cy.elements(`#${val}`));
  }
  
  /**
   * Luckily for us, we don't have to actually use Cytoscape!
   * We use CSS styles to "convey" a selected node to the user. But we don't actually "select" a node
   * in Cytoscape, as one might regularly.
   * @param sel The ID of the node that we want to render as "selected". Can be an edge or node.
   */
  private selectNodeOrEdgeInInstance(sel: NodeCollection) {
    // "de-selects" all of the other nodes
    this.cy.elements().not(sel).removeClass(STYLE_CLASSES.SELECTED);
  
    if (sel) {
      // Causes the node to render as "selected" in the UI.
      sel.addClass(STYLE_CLASSES.SELECTED);
    }
  }

  public generateInitialCytoscapeConfig(): cytoscape.CytoscapeOptions {
    return {
      layout: {
        name: 'dagre',
        nodeDimensionsIncludeLabels: true,
        animate: true,
        // animationEasing: 'cubic',
        spacingFactor: 1.15,
        padding: 10,
        // @ts-ignore
        edgeSep: 100,
        ...this.layout
      },
  
      boxSelectionEnabled: false,
      autounselectify: true,
      minZoom: 0.5,
      maxZoom: 4,
  
      style: [...Object.values(this.stylesheet), ...baseCytoscapeStyles],
  
      elements: this.elements || {
        // Prevents a "default" node from rendering when the list is empty...
        nodes: []
      },
      
      ...this.config
    };
  }
  
  public setupEventHandlers(cy: cytoscape.Core) {
    function addHighlight(e: EventObject) {
      const sel = e.target;
      cy.elements().not(sel).addClass('semitransp');
      sel.addClass('highlight');
    }
    
    function removeHighlight(e: EventObject) {
      const sel = e.target;
      cy.elements().removeClass('semitransp');
      sel.removeClass('highlight');
    }
    
    cy.on('mouseover', 'node', addHighlight);
    cy.on('mouseout', 'node', removeHighlight);
    cy.on('mouseover', 'edge', addHighlight);
    cy.on('mouseout', 'edge', removeHighlight);
  
    // Apparently 'tap' isn't in the type definitions for this package... But it's in the docs!
    // Tap is a "click" that works for both Touch and Mouse based interfaces.
    // @ts-ignore
    cy.on('tap', 'node', e => {
      this.selectNodeOrEdgeInInstance(e.target);
      
      this.selectNode(e.target._private.data.id);
    });
    
    // @ts-ignore
    cy.on('tap', 'edge', e => {
      this.selectNodeOrEdgeInInstance(e.target);
  
      this.selectEdge(e.target._private.data.id);
    });
  }
  
  public mounted() {
    if (!this.$refs.container) {
      return null;
    }
    
    const config = this.generateInitialCytoscapeConfig();
  
    // Have to cast to specifically HTMLElement for this to work.
    config.container = this.$refs.container as HTMLElement;
    
    this.cy = cytoscape(config);
    
    this.setupEventHandlers(this.cy);
    
    this.$forceUpdate();
    
  }
  
  public beforeDestroy() {
    if (!this.cy) {
      return;
    }
    
    // Kill the container gracefully
    this.cy.destroy();
  }
 
  public render(h: CreateElement): VNode {
    if (!this.$refs.container) {
      return (
        <div ref="container" class="graph-container">
          <h1>Please wait while the graph is loading...</h1>
        </div>
      );
    }
    
    return (
      <div ref="container" class="graph-container">
      </div>
    );
  }
}
