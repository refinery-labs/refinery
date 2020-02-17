import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import cytoscape, { EdgeDefinition, EventObject, LayoutOptions, NodeDefinition } from 'cytoscape';
import cyCanvas, { CytoscapeCanvasInstance } from '../lib/cytoscape-canvas';
import deepEqual from 'fast-deep-equal';
import { animationBegin, animationEnd, baseCytoscapeStyles, STYLE_CLASSES } from '@/lib/cytoscape-styles';
import { timeout } from '@/utils/async-utils';
import { CyElements, CyStyle, CytoscapeGraphProps } from '@/types/cytoscape-types';
import { registerCustomDagre } from '@/lib/dagre-cytoscape';
import { CyTooltip, DemoTooltip, TooltipType } from '@/types/demo-walkthrough-types';

// @ts-ignore
cytoscape.use(registerCustomDagre);
cyCanvas(cytoscape);

interface CytoscapeLayer {
  layer: CytoscapeCanvasInstance;
  ctx: CanvasRenderingContext2D;
}

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

function hashCode(str: string) {
  var hash = 0,
    i,
    chr;
  if (str.length === 0) return hash;
  for (i = 0; i < str.length; i++) {
    chr = str.charCodeAt(i);
    hash = (hash << 5) - hash + chr;
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
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

  @Prop({ required: true }) public clearSelection!: () => void;
  @Prop({ required: true }) public selectNode!: (id: string) => void;
  @Prop({ required: true }) public selectEdge!: (id: string) => void;
  @Prop({ required: true }) public nextTooltip!: () => void;
  @Prop({ required: true }) public loadCyTooltips!: (cy: cytoscape.Core) => void;

  @Prop() public currentTooltips!: CyTooltip[];
  @Prop() public selected!: string | null;
  @Prop() public enabledNodeIds!: string[] | null;
  @Prop() public backgroundGrid!: boolean;
  @Prop() public windowWidth?: number;
  @Prop() public animationDisabled?: boolean;

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

    if (!this.cy) {
      return;
    }

    // Re-run the layout...
    const layout = this.cy.layout(this.getLayoutConfig(false));
    layout.promiseOn('layoutstop').then(async () => {
      // Small delay while we wait for the layout
      await timeout(50);

      this.isLayoutRunning = false;

      if (this.selected) {
        this.selectNodeOrEdgeInInstance(this.selected);
      }
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
    // Force override to disable the animation. Cytoscape animations can be janky :/
    if (this.animationDisabled) {
      animate = false;
    }

    return {
      name: 'dagre',
      nodeDimensionsIncludeLabels: true,
      animate,
      // animationEasing: 'cubic',
      spacingFactor: 1.15,
      padding: 20,
      // @ts-ignore
      edgeSep: 100,
      rankSep: 70,
      align: 'UL',
      ...this.layout
    };
  }

  public generateInitialCytoscapeConfig(): cytoscape.CytoscapeOptions {
    return {
      layout: this.getLayoutConfig(true),

      boxSelectionEnabled: false,
      autounselectify: true,
      minZoom: 0.25,
      maxZoom: 4,
      wheelSensitivity: 0.8,

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
      if (this.tooltipTapped(cy, e)) {
        this.nextTooltip();
      } else if (e.target === cy) {
        // Tap on background of canvas
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

  private getBottomCyLayer(cy: cytoscape.Core): CytoscapeLayer | null {
    // @ts-ignore
    const getLayer: (args?: any) => CytoscapeCanvasInstance = args => cy.cyCanvas(args);

    const bottomLayer = getLayer({
      zIndex: -1
    });
    const canvas = bottomLayer.getCanvas();
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      return null;
    }
    return {
      layer: bottomLayer,
      ctx: ctx
    };
  }

  public drawBackground(cyLayer: CytoscapeLayer) {
    const { layer, ctx } = cyLayer;

    if (!this.backgroundGrid) {
      return;
    }

    layer.resetTransform(ctx);
    layer.clear(ctx);
    layer.setTransform(ctx);

    layer.drawGrid(ctx);
  }

  public drawTooltips(cyLayer: CytoscapeLayer) {
    const { ctx } = cyLayer;
    this.currentTooltips.forEach(tooltip => {
      const contentHash = this.tooltipHash(tooltip);
      if (this.$refs[contentHash]) {
        //@ts-ignore
        ctx.drawImage(this.$refs[contentHash], tooltip.x + tooltip.offsetX, tooltip.y + tooltip.offsetY);
      }
    });
  }

  public setupCanvasBackground(cy: cytoscape.Core) {
    const cyLayer = this.getBottomCyLayer(cy);
    if (!cyLayer) {
      return;
    }

    // Draw a background
    cy.on('render cyCanvas.resize', evt => {
      this.drawBackground(cyLayer);
      this.drawTooltips(cyLayer);
    });
  }

  private tooltipTapped(cy: cytoscape.Core, event: EventObject): boolean {
    const cyLayer = this.getBottomCyLayer(cy);
    if (!cyLayer) {
      return false;
    }
    const { layer, ctx } = cyLayer;

    return (
      this.currentTooltips.filter(tooltip => {
        const img = this.$refs[this.tooltipHash(tooltip)] as HTMLImageElement;
        return layer.tooltipTapped(ctx, tooltip, img, event.position);
      }).length > 0
    );
  }

  public tooltipHash(tooltip: CyTooltip) {
    return hashCode(tooltip.header + tooltip.body);
  }

  public renderTooltipSVG(tooltip: CyTooltip) {
    var data = `
  <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
    <foreignObject width="100%" height="100%">
      <div xmlns="http://www.w3.org/1999/xhtml" style="">
        <style>
        * {
          font-size: .875rem;
        }
        .btn {
          background: transparent;
          border: .05rem solid #fff;
          border-radius: .1rem;
          color: #fff;
          cursor: pointer;
          display: inline-block;
          outline: none;
          margin: 0 .2rem;
          padding: .35rem;
          text-align: center;
          text-decoration: none;
          -webkit-transition: all .2s ease;
          transition: all .2s ease;
          vertical-align: middle;
          white-space: nowrap;
          font-size: .6rem;
        }
        .step {
          color: white;
          background: #50596c;
          max-width: 320px;
          border-radius: 3px;
          -webkit-filter: drop-shadow(0 0 2px rgba(0, 0, 0, 0.5));
          filter: drop-shadow(0 0 2px rgba(0, 0, 0, 0.5));
          padding: 1rem;
          text-align: center;
        }
        .header {
          margin: -1rem -1rem .5rem;
          padding: .5rem;
          background-color: #454d5d;
          border-top-left-radius: 3px;
          border-top-right-radius: 3px;
        }
        .content {
          font-size: .7rem;
          margin-bottom: .5rem;
        }
        </style>
        <div class="step">
          <div class="header">
            ${tooltip.header}
          </div>
          <div class="content">
            ${tooltip.body}
          </div>
            <button class="btn">
              continue
            </button>
        </div>
      </div>
    </foreignObject>
  </svg>`;

    const DOMURL = window.URL || window.webkitURL || window;

    const svg = new Blob([data], {
      type: 'image/svg+xml;charset=utf-8'
    });
    const url = DOMURL.createObjectURL(svg);

    const contentHash = this.tooltipHash(tooltip);
    return <img src={url} ref={contentHash} />;
  }

  public loadTooltips() {
    const svgs = this.currentTooltips.map(tooltip => this.renderTooltipSVG(tooltip));
    return <div style="display:none">{svgs}</div>;
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

    this.loadCyTooltips(this.cy);
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

    if (this.currentTooltips.length > 0) {
      const eles = this.cy.$(`#${this.currentTooltips[0].id}`);
      console.log(this.windowWidth);

      const viewPort = Math.min(this.cy.width(), this.cy.height());
      if (viewPort <= 450) {
        this.cy.fit(eles, 100);
      } else if (viewPort <= 800) {
        this.cy.fit(eles, 250);
      } else {
        this.cy.fit(eles, (viewPort - 200) / 2);
      }
      this.cy.panBy({
        x: -150,
        y: 0
      });
    }

    return (
      <div ref="container" class="graph-container">
        {this.loadTooltips()}
      </div>
    );
  }
}
