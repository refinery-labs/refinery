import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import cytoscape, { EdgeDefinition, EventObject, LayoutOptions, NodeDefinition } from 'cytoscape';
import cyCanvas, { CytoscapeCanvasInstance } from '../lib/cytoscape-canvas';
import dagre from 'cytoscape-dagre';
import deepEqual from 'fast-deep-equal';
import { WorkflowRelationship, WorkflowState } from '@/types/graph';
import { animationBegin, animationEnd, baseCytoscapeStyles, STYLE_CLASSES } from '@/lib/cytoscape-styles';
import { timeout } from '@/utils/async-utils';
import { CyElements, CyStyle, CytoscapeGraphProps } from '@/types/cytoscape-types';

cytoscape.use(dagre);
cyCanvas(cytoscape);

function areCytoResourcesTheSame(a: NodeDefinition | EdgeDefinition, b: NodeDefinition | EdgeDefinition): boolean {
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);

  if (aKeys.length !== bKeys.length) {
    return false;
  }

  const ignoredKeys = ['scratch', 'scatch'];

  // If anything returns true, the output will be true.
  const differencesExist = aKeys.some(key => {
    // Ignore these keys because they are known to be "dirty" data for plugins, etc
    if (ignoredKeys.indexOf(key) !== -1) {
      return false;
    }

    // Key doesn't exist on object
    if (!b.hasOwnProperty(key)) {
      return true;
    }

    // This is a safe operation because we know that both objects have the following key
    // @ts-ignore
    return !deepEqual(a[key], b[key]);
  });

  return !differencesExist;
}

// TODO: Likely we just want to use fast-deep-equal but probably not look at Scratch data?
function areCytoGraphsTheSame(val: CyElements, oldVal: CyElements) {
  // Something is null, graphs are definitely different.
  // TODO: Do we need to compare is the nodes or edges are both null from previous values?
  // For now, lets assume that all input is well-formed. Typescript lets up have it be well-formed...
  if (!val || !val.nodes || !val.edges || !oldVal || !oldVal.nodes || !oldVal.edges) {
    return false;
  }

  const graphsAreSameLength = val.nodes.length === oldVal.nodes.length && val.edges.length === oldVal.edges.length;

  // If graphs have different lengths, then they have certainly changed.
  if (!graphsAreSameLength) {
    return false;
  }

  // Ensure that all nodes haven't moved or anything funky
  const nodesHaveDifferences = val.nodes.some((node, i) => !areCytoResourcesTheSame(node, oldVal.nodes[i]));

  if (nodesHaveDifferences) {
    return false;
  }

  // Ensure that all edges haven't moved or anything funky
  const edgesHaveDifferences = val.edges.some((edge, i) => !areCytoResourcesTheSame(edge, oldVal.edges[i]));

  if (edgesHaveDifferences) {
    return false;
  }

  // The graphs are equivalent according to our limited logic.
  return true;
}

@Component
export default class CytoscapeGraph extends Vue implements CytoscapeGraphProps {
  cy!: cytoscape.Core;
  playAnimation!: boolean;
  isLayoutRunning!: boolean;
  currentAnimationGroupNonce!: number;

  @Prop({ required: true }) public elements!: CyElements;
  @Prop() public layout!: LayoutOptions | null;
  @Prop({ required: true }) public stylesheet!: CyStyle;

  @Prop({ required: true }) public clearSelection!: () => {};
  @Prop({ required: true }) public selectNode!: (element: WorkflowState) => {};
  @Prop({ required: true }) public selectEdge!: (element: WorkflowRelationship) => {};
  @Prop() public selected!: string | null;
  @Prop() public enabledNodeIds!: string[] | null;
  @Prop() public backgroundGrid!: boolean;
  @Prop() public windowWidth?: number;

  // This is a catch-all for any additional options that need to be specified
  @Prop({ default: () => {} }) public config!: cytoscape.CytoscapeOptions | null;

  public cytoscapeValueModified() {
    if (!this.cy) {
      // TODO: Make this development only?
      console.error('Graph not loaded yet and elements were modified!');
      return;
    }

    // Tells the Cytoscape graph to update. The library internally diffs elements based on their ID.
    this.cy.json(this.generateInitialCytoscapeConfig());

    this.selectNodeOrEdgeInInstance(this.selected);
  }

  @Watch('elements')
  private async elementsModified(val: CyElements, oldVal: CyElements) {
    if (val === oldVal) {
      return;
    }

    // Don't re-layout because the graphs haven't changed
    if (areCytoGraphsTheSame(val, oldVal)) {
      return;
    }

    this.isLayoutRunning = true;

    this.cytoscapeValueModified();

    // Re-run the layout...
    const layout = this.cy.layout(this.getLayoutConfig(false));
    layout.promiseOn('layoutstop').then(async () => {
      // Small delay while we wait for the layout
      await timeout(50);

      this.isLayoutRunning = false;
    });

    layout.run();
  }

  @Watch('layout', { deep: true })
  private layoutModified(val: LayoutOptions, oldVal: LayoutOptions) {
    if (val === oldVal) {
      return;
    }

    this.cytoscapeValueModified();
  }

  @Watch('stylesheet', { deep: true })
  private styleModified(val: CyStyle, oldVal: CyStyle) {
    if (val === oldVal) {
      return;
    }

    this.cytoscapeValueModified();
  }

  @Watch('config', { deep: true })
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

    this.selectNodeOrEdgeInInstance(val);
  }

  @Watch('windowWidth')
  private windowWidthModified(val?: number, oldVal?: number) {
    if (val === oldVal || !this.cy) {
      return;
    }

    // Fixes the issue of Cytoscape getting funky when the window size changes.
    this.cy.resize();
  }

  @Watch('enabledNodeIds', { immediate: true })
  private enabledNodeIdsChanged(val: string[], oldVal: string[]) {
    if (val === oldVal || !this.cy) {
      return;
    }

    this.playAnimation = false;

    const animationNonce = Math.round(Math.random() * 10000000000000000);
    this.currentAnimationGroupNonce = animationNonce;

    const elements = val && val.map(id => this.cy.getElementById(id));

    // This optimizes performance by only running the calculations "once" afterwards
    this.cy.batch(() => {
      // Reset all elements
      this.cy
        .elements()
        .removeClass(STYLE_CLASSES.DISABLED)
        // Kill all ongoing animations
        .stop(true, true);

      // We don't need to disable any elements, so return
      if (!val || val.length === 0) {
        return;
      }

      // Disable everything. We will manually re-enable things that we want to keep enabled.
      this.cy.elements('node').addClass(STYLE_CLASSES.DISABLED);

      // TODO: Figure out if we want to "disable" edges?
      // this.cy.elements('edge').addClass(STYLE_CLASSES.DISABLED);

      // Don't "disable" the main node.
      this.cy.elements(`#${this.selected}`).removeClass(STYLE_CLASSES.DISABLED);

      this.playAnimation = true;

      elements.forEach(ele =>
        ele.addClass(STYLE_CLASSES.SELECTION_ANIMATION_ENABLED).removeClass(STYLE_CLASSES.DISABLED)
      );
    });

    // Skip animation if we don't have any values.
    if (!val) {
      return;
    }

    // This is so garbage, but it works pretty well.
    const runAnimationLoop = async () => {
      // Break out of this looping animation hellscape
      if (animationNonce !== this.currentAnimationGroupNonce) {
        return;
      }

      const startPromises = elements.map(ele =>
        ele
          .animation(animationBegin)
          .play()
          .promise('completed')
      );

      await Promise.all(startPromises);

      const endPromises = elements.map(ele =>
        ele
          .animation(animationEnd)
          .play()
          .promise('completed')
      );

      await Promise.all(endPromises);

      // Break out of this looping animation hellscape
      if (animationNonce !== this.currentAnimationGroupNonce) {
        return;
      }

      await timeout(1200);

      // Break out of this looping animation hellscape
      if (this.playAnimation && animationNonce === this.currentAnimationGroupNonce) {
        runAnimationLoop();
      }
    };

    runAnimationLoop();
  }

  /**
   * Luckily for us, we don't have to actually use Cytoscape!
   * We use CSS styles to "convey" a selected node to the user. But we don't actually "select" a node
   * in Cytoscape, as one might regularly.
   * @param nodeId The ID of the node that we want to render as "selected". Can be an edge or node.
   */
  private selectNodeOrEdgeInInstance(nodeId: string | null) {
    // We don't have a valid selector, so just deselect everything (unless it is a number)
    if (typeof nodeId !== 'number' && !nodeId) {
      this.cy.elements().removeClass(STYLE_CLASSES.SELECTED);
      return;
    }

    const selectById = `[id = "${this.selected}"]`;

    const sel = this.cy.elements(selectById);

    // "de-selects" all of the other nodes
    this.cy
      .elements()
      .not(sel)
      .removeClass(STYLE_CLASSES.SELECTED);

    if (sel && sel.length > 0) {
      // Causes the node to render as "selected" in the UI.
      sel.addClass(STYLE_CLASSES.SELECTED);

      // Skip the animation
      if (this.isLayoutRunning) {
        this.cy.center(sel);

        return;
      }

      this.cy.animate(
        {
          center: {
            eles: sel
          },
          easing: 'ease-out'
        },
        {
          duration: 200
        }
      );
    }
  }

  public getLayoutConfig(animate: boolean) {
    return {
      name: 'dagre',
      nodeDimensionsIncludeLabels: true,
      animate,
      // animationEasing: 'cubic',
      spacingFactor: 1.15,
      padding: 108,
      // @ts-ignore
      edgeSep: 100,
      ...this.layout
    };
  }

  public generateInitialCytoscapeConfig(): cytoscape.CytoscapeOptions {
    return {
      layout: this.getLayoutConfig(true),

      boxSelectionEnabled: false,
      autounselectify: true,
      minZoom: 0.5,
      maxZoom: 4,

      style: [...Object.values(this.stylesheet), ...baseCytoscapeStyles],

      elements: this.elements || {
        // Prevents a "default" node from rendering when the list is empty...
        nodes: [],
        edges: []
      },

      ...this.config
    };
  }

  public setupEventHandlers(cy: cytoscape.Core) {
    function addHighlight(e: EventObject) {
      const sel = e.target;
      cy.elements()
        .not(sel)
        .addClass('semitransp');
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

    cy.on('tap', e => {
      // Tap on background of canvas
      if (e.target === cy) {
        this.clearSelection();
      }
    });

    // Apparently 'tap' isn't in the type definitions for this package... But it's in the docs!
    // Tap is a "click" that works for both Touch and Mouse based interfaces.
    // @ts-ignore
    cy.on('tap', 'node', e => {
      this.selectNode(e.target.id());
    });

    // @ts-ignore
    cy.on('tap', 'edge', e => {
      this.selectEdge(e.target.id());
    });
  }

  public setupCanvasBackground(cy: cytoscape.Core) {
    // @ts-ignore
    const getLayer: (args?: any) => CytoscapeCanvasInstance = args => cy.cyCanvas(args);

    const bottomLayer = getLayer({
      zIndex: -1
    });
    const canvas = bottomLayer.getCanvas();
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      return;
    }

    // Draw a background
    cy.on('render cyCanvas.resize', evt => {
      if (!this.backgroundGrid) {
        return;
      }

      bottomLayer.resetTransform(ctx);
      bottomLayer.clear(ctx);
      bottomLayer.setTransform(ctx);

      bottomLayer.drawGrid(ctx);
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

    // Re-select the node on the graph
    this.selectNodeOrEdgeInInstance(this.selected);

    this.setupCanvasBackground(this.cy);

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

    return <div ref="container" class="graph-container" />;
  }
}
