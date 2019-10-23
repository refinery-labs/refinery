import { Graph } from 'graphlib';

export type SubGraphLookup = { [key: string]: number };

export interface GraphHelperConstructor extends Function {
  prototype: GraphHelper;
  new (...args: any[]): GraphHelper;
}

export interface SerializedGraph {
  edges: { v: string; w: string; name: string }[];
  nodes: { v: string; value: Object }[];
  options: {
    compound: boolean;
    directed: boolean;
    multigraph: boolean;
  };
  value: {
    height: number;
    ranker: string;
    ranksep: string;
    width: number;
  };
}

export interface GraphHelper {
  createEmptyGraph(): Graph;
  createSubGraphLookup(g: Graph): SubGraphLookup;
  convertSubGraphLookupIntoGraphs(parentGraph: Graph, idToGraphLookup: SubGraphLookup): Graph[];
  sliceGraphIntoSubgraphs(graph: Graph): Graph[];
}
