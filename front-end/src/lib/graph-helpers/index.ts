import { Graph, json } from 'graphlib';
import { deepJSONCopy } from '@/lib/general-utils';
import { GraphHelper, SerializedGraph, SubGraphLookup } from './types';

export * from './types';

/**
 * A set of helpers for manipulating graph data. They live inside of this class to make stubbing for testing easier.
 */
export class BaseGraphHelper implements GraphHelper {
  /**
   * This is used by Dagre to store configuration info -- but it's technically just a string.
   */
  graphConfig!: string;

  constructor(graphConfig: string) {
    this.graphConfig = graphConfig;
  }

  /**
   * Creates a Dagre-compatible graph instance.
   */
  createEmptyGraph() {
    // Docs here: https://github.com/dagrejs/graphlib/wiki/API-Reference
    const graph = new Graph({
      multigraph: true,
      compound: true
    });

    // This step is important for Dagre to successfully run it's layout.
    // This should just be a string, per the docs, but instead it is an object. :)
    graph.setGraph(deepJSONCopy(this.graphConfig));

    // Copied from Dagre-Cytoscape -- likely needed because we are storing an Object in the string field.
    graph.setDefaultEdgeLabel(function() {
      return {};
    });
    graph.setDefaultNodeLabel(function() {
      return {};
    });

    return graph;
  }

  /**
   * For a graph that consists of multiple independent graphs (no edges between the nodes), this function will
   * figure out what "graph number" a given node belongs to by spidering through the given graph.
   * This is useful for running the Dagre layout on each independent graph to have better visual results.
   *
   * Nodes are grouped by a number. If a graph has 2 independent graphs in it, then some nodes will be 0 and others 1.
   * @param graph {Graph} The graph to traverse for sub-graphs.
   * @returns {SubGraphLookup} A dictionary of NodeId -> Graph Number
   */
  createSubGraphLookup(graph: Graph): SubGraphLookup {
    function addNodesToLookup(idToGraph: SubGraphLookup, node: string, i: number) {
      // Check if the node hasn't been seen yet
      if (idToGraph[node] === undefined) {
        // Assign it to it's own graph
        idToGraph[node] = i;

        // Get all nodes connecting to the current node.
        const neighbors = graph.neighbors(node);

        // Connect every neighbor to our current graph and recurse
        if (neighbors) {
          neighbors.forEach(n => addNodesToLookup(idToGraph, n, i));
        }
      }

      return idToGraph;
    }

    return graph.sinks().reduce(addNodesToLookup, {} as SubGraphLookup);
  }

  /**
   * Generates subgraphs for a given parent graph and a dictionary of NodeId -> "Graph Number".
   * This allows you to take a graph with multiple disconnected sub-graphs and generate them into Dagre-compatible
   * graphs to perform a layout on.
   * @param parentGraph {Graph} Graphlib instance that holds the nodes specified in the idToGraphLookup
   * @param idToGraphLookup {SubGraphLookup} Mapping from NodeId -> "Graph Number", where every NodeId appears in graph.
   */
  convertSubGraphLookupIntoGraphs(parentGraph: Graph, idToGraphLookup: SubGraphLookup): Graph[] {
    // Serialize the parent graph so that we can manipulate it's contents without magic
    const jsonParentGraph = json.write(parentGraph) as SerializedGraph;

    // Every subgraph that is returned will be stored here.
    const subGraphs: SerializedGraph[] = [];

    // Get the maximum value from the lookup, which is the number of unique graphs to generate
    const numberOfGraphs = Object.values(idToGraphLookup).reduce((max, cur) => {
      // If the index is higher than the current, set it as the maximum.
      if (max < cur) {
        return cur;
      }

      return max;
    });

    // Create instances for every subgrab
    for (let i = 0; i <= numberOfGraphs; i++) {
      // Make a clone of the parent graph
      const clone = deepJSONCopy(jsonParentGraph);

      // Clear all of the node and edge data.
      clone.edges = [];
      clone.nodes = [];

      subGraphs.push(clone);
    }

    // Add everything to
    Object.keys(idToGraphLookup).forEach(node => {
      // Grabs the subgraph by index to add the node too
      const graph = subGraphs[idToGraphLookup[node]];

      // If a node is missing from the parent graph, we will throw.
      if (graph === undefined) {
        throw new Error('Missing index for graph: ' + node);
      }

      // Find the matching node and push that to the output.
      const matchingNode = jsonParentGraph.nodes.find(n => n.v === node);

      // We push if it's a matching node for the graph.
      if (matchingNode) {
        graph.nodes.push(matchingNode);
      }

      // Find all matching edges and push them into the output.
      const matchingEdges = jsonParentGraph.edges.filter(e => e.v === node);

      matchingEdges.forEach(e => graph.edges.push(e));
    });

    // Read the JSON data back into Graphlib
    return subGraphs.map(json.read);
  }

  /**
   * Given a Graph, this will split it up into sub-graphs of the nodes that weren't connected in the given graph.
   * @param graph {Graph} Graph to perform split operation on.
   */
  sliceGraphIntoSubgraphs(graph: Graph): Graph[] {
    return this.convertSubGraphLookupIntoGraphs(graph, this.createSubGraphLookup(graph));
  }
}
