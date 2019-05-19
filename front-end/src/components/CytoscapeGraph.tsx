import {CreateElement, VNode} from 'vue';
import {Component, Prop, Vue, Watch} from 'vue-property-decorator';
import cytoscape, {ElementDefinition, ElementsDefinition, LayoutOptions, Stylesheet} from 'cytoscape';
import dagre from 'cytoscape-dagre';

cytoscape.use(dagre);

type CyElements = ElementsDefinition | ElementDefinition[] | Promise<ElementsDefinition> | Promise<ElementDefinition[]>;
type CyStyle = Stylesheet[] | Promise<Stylesheet[]>;

@Component
export default class CytoscapeGraph extends Vue {
  cy!: cytoscape.Core;
  
  @Prop({required: true}) private elements!: CyElements;
  @Prop() private layout!: LayoutOptions;
  @Prop({required: true}) private stylesheet!: CyStyle;
  
  // This is a catch-all for any additional options that need to be specified
  @Prop({default: () => {}}) private config!: cytoscape.CytoscapeOptions;
  
  public cytoscapeValueModified(val: object) {
    if (!this.cy) {
      // TODO: Make this development only?
      console.error('Graph not loaded yet and elements were modified!');
      return;
    }
  
    // Tells the Cytoscape graph to update. The library internally diffs elements based on their ID.
    this.cy.json(val);
  }
  
  @Watch('elements', {deep: true})
  private elementsModified(val: CyElements, oldVal: CyElements) {
    this.cytoscapeValueModified({
      elements: val
    });
  }
  
  @Watch('layout', {deep: true})
  private layoutModified(val: LayoutOptions, oldVal: LayoutOptions) {
    this.cytoscapeValueModified({
      layout: val
    });
  }
  
  @Watch('stylesheet', {deep: true})
  private styleModified(val: CyStyle, oldVal: CyStyle) {
    this.cytoscapeValueModified({
      style: val
    });
  }
  
  @Watch('config', {deep: true})
  private configModified(val: cytoscape.CytoscapeOptions, oldVal: cytoscape.CytoscapeOptions) {
    this.cytoscapeValueModified({
      ...val
    });
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
  
      style: this.stylesheet,
  
      elements: this.elements || {
        // Prevents a "default" node from rendering when the list is empty...
        nodes: []
      },
      
      ...this.config
    };
  }
  
  public mounted() {
    if (!this.$refs.container) {
      return null;
    }
    
    const config = this.generateInitialCytoscapeConfig();
    console.log(config);
  
    // Have to cast to specifically HTMLElement for this to work.
    config.container = this.$refs.container as HTMLElement;
    
    this.cy = cytoscape(config);
    
    this.$forceUpdate();
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
