import { DagreBoundingBox, DagreOptions, DagrePosition, RankerAlgorithms } from './types';
import { CollectionReturnValue } from 'cytoscape';
import { Graph, json } from 'graphlib';
import { BaseGraphHelper, GraphHelper, SerializedGraph } from '@/lib/graph-helpers';

const isFunction = function(o: any) {
  return typeof o === 'function';
};
const dagre = require('dagre');

/**
 * A fork of the Dagre-Cytoscape library, with major refactoring added.
 */
export class DagreLayout implements DagreOptions {
  cy!: cytoscape.Core;
  eles!: CollectionReturnValue;

  graphCreator!: GraphHelper;

  // Dagre algorithm default options
  nodeSep?: number;
  edgeSep?: number;
  rankSep?: number;
  rankDir?: string;
  ranker?: RankerAlgorithms = RankerAlgorithms.NetworkSimplex;
  minLen = (edge: any) => 1;
  edgeWeight = (edge: any) => 1;

  // general layout options
  fit: boolean = true;
  padding: number = 30;
  spacingFactor?: number;
  nodeDimensionsIncludeLabels: boolean = false;
  // specific padding between chains of blocks
  subGraphPadding: number = 60;

  animate: boolean = false;
  animateFilter = (node: any, i: number) => true;
  animationDuration = 500;
  animationEasing?: number;

  boundingBox?: DagreBoundingBox;
  transform = (node: any, pos: DagrePosition) => pos;

  ready = () => {};
  stop = () => {};

  constructor(options: DagreOptions & { cy: cytoscape.Core; eles: CollectionReturnValue }, graphCreator?: GraphHelper) {
    this.cy = options.cy;
    this.eles = options.eles;

    // NOTE!!!
    // This is not a string!
    // The person that wrote this library is abusing this in Graphlib to be a pointer (object) instead.
    // What the heck is going on here?
    this.graphCreator =
      graphCreator ||
      // @ts-ignore
      new BaseGraphHelper({
        nodesep: options.nodeSep,
        edgesep: options.edgeSep,
        ranksep: options.rankSep,
        rankDir: options.rankDir,
        ranker: options.ranker
      });

    // Override any values of this class with the specified options.
    Object.assign(this, options);
  }

  /**
   * This leverages a getter so that we can wrap the `this` context properly.
   * Cytoscape is terrifying.
   */
  get run() {
    const self = this;

    // Return a function from the getter so that the caller can call this like they were just calling `instance.run()`
    return function runFn() {
      // Keep a copy of the `this` context here, since it's being overridden by Cytoscape instead of passing arguments.
      // @ts-ignore
      const layout: cytoscape.CoreEvents = this;

      // Call our actual layout function and pass the `this` context as an argument instead.
      self.runLayout(layout);
    };
  }

  /**
   * Grabs elements from Cytoscape and puts them into the given Graph instance.
   * @param graph {Graph} The Graphlib instance to add the elements to.
   * @param eles {CollectionReturnValue} The Cytoscape elements to read from.
   */
  addCytoscapeElementsToGraph(graph: Graph, eles: CollectionReturnValue) {
    function getVal<TElement, TReturn>(ele: TElement, val: (el: TElement) => TReturn) {
      return isFunction(val) ? val.call(ele, ele) : val;
    }

    // add nodes to dagre
    let nodes = eles.nodes();

    for (let i = 0; i < nodes.length; i++) {
      let node = nodes[i];

      // Get the size of the node from Cytoscape.
      let nbb = node.layoutDimensions({
        nodeDimensionsIncludeLabels: this.nodeDimensionsIncludeLabels
      });

      // Add node to the graph.
      graph.setNode(node.id(), {
        width: nbb.w,
        height: nbb.h,
        name: node.id()
      });
    }

    // set compound parents
    for (let i = 0; i < nodes.length; i++) {
      let node = nodes[i];

      if (node.isChild()) {
        // @ts-ignore
        graph.setParent(node.id(), node.parent().id());
      }
    }

    // add edges to dagre
    let edges = eles
      .edges()
      // dagre can't handle edges on compound nodes
      .filter(edge => !edge.source().isParent() && !edge.target().isParent());

    for (let i = 0; i < edges.length; i++) {
      let edge = edges[i];

      // Add the edge to the graph with data from Cytoscape
      graph.setEdge(
        edge.source().id(),
        edge.target().id(),
        {
          minlen: getVal(edge, this.minLen),
          weight: getVal(edge, this.edgeWeight),
          name: edge.id()
        },
        edge.id()
      );
    }

    return graph;
  }

  /**
   * Triggers Dagre to run a layout for the elements in the graph.
   * This then stores the data inside of Cytoscape's scratchpad for future rendering.
   * @param graph {Graph} The Graphlib instance to perform the layout on.
   * @param offsetX {number} Value to store inside of Cytoscape to offset the graph by at layout time.
   * @return {boolean} Whether or not the subgraph should be padded when drawn.
   */
  runLayoutForNodes(graph: Graph, offsetX: number): boolean {
    let cy = this.cy;

    dagre.layout(graph);

    let padSubgraph = false;
    let gNodeIds = graph.nodes();
    for (let i = 0; i < gNodeIds.length; i++) {
      let id = gNodeIds[i];
      let n = graph.node(id);

      const scratch = cy.getElementById(id).scratch();
      scratch.groupOffsetX = offsetX;
      scratch.dagre = n;
      padSubgraph = padSubgraph || scratch._tooltip;
    }
    return padSubgraph;
  }

  /**
   * Runs the layout for the graph.
   */
  runLayout(layout: cytoscape.CoreEvents) {
    const parentGraph = this.graphCreator.createEmptyGraph();

    // We create this first so that we can understand the relationships between every node
    this.addCytoscapeElementsToGraph(parentGraph, this.eles);

    // Slice the graph into each unconnected chunk
    const subGraphs = this.graphCreator.sliceGraphIntoSubgraphs(parentGraph);

    // Starting offset is a small number that represents a left-hand margin.
    let offsetX = 80;

    subGraphs.map(subGraph => {
      const shouldPadSubgraph = this.runLayoutForNodes(subGraph, offsetX);

      let graphWidth = (json.write(subGraph) as SerializedGraph).value.width;

      // If the width is invalid, then set a sane default.
      if (graphWidth < 100 || isNaN(graphWidth)) {
        graphWidth = 100;
      }

      // Keep track of where the previous graph was and add a slight offset. This prevents overlaps from happening.
      offsetX += (shouldPadSubgraph ? 200 : 60) + graphWidth;
    });

    const nodes = this.eles.nodes();

    // Triggers Cytoscape to ask for new positions for every element.
    nodes.layoutPositions(layout, this as any, function(ele: any) {
      // Grab data that was stored away inside of Cytoscape in their "Scratchpad"
      const scratch = ele.scratch();
      const offsetX = scratch.groupOffsetX;
      const dModel = scratch.dagre;

      return {
        // Offset is used to understand where to render this on the graph.
        // Because we have many graphs, they would overlap without this offset.
        x: dModel.x + offsetX,
        y: dModel.y
      };
    });

    return this; // chaining
  }
}
