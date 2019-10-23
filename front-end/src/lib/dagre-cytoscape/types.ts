export interface DagreBoundingBox {
  x1: number;
  y1: number;
  x2?: number;
  y2?: number;
  w?: number;
  h?: number;
}

export interface DagrePosition {}

export enum RankerAlgorithms {
  NetworkSimplex = 'network-simplex',
  TightTree = 'tight-tree',
  LongestPath = 'longest-path'
}

export interface DagreOptions {
  /**
   * the separation between adjacent nodes in the same rank
   */
  nodeSep?: number;
  /**
   * the separation between adjacent edges in the same rank
   */
  edgeSep?: number;
  /**
   * the separation between adjacent nodes in the same rank
   */
  rankSep?: number;
  /**
   * 'TB' for top to bottom flow, 'LR' for left to right,
   */
  rankDir?: string;
  /**
   * Type of algorithm to assigns a rank to each node in the input graph.
   */
  ranker?: RankerAlgorithms;
  /**
   * number of ranks to keep between the source and target of the edge
   * @param edge Edge to determine number of ranks for.
   */
  minLen?: (edge: any) => number;
  /**
   * higher weight edges are generally made shorter and straighter than lower weight edges
   * @param edge Edge to determine weight number for.
   */
  edgeWeight?: (edge: any) => number;

  // general layout options;
  /**
   * whether to fit to viewport
   */
  fit?: boolean;
  /**
   * fit padding
   */
  padding?: number;
  /**
   * Applies a multiplicative factor (>0) to expand or compress the overall area that the nodes take up
   */
  spacingFactor?: number;
  /**
   * whether labels should be included in determining the space used by a node
   */
  nodeDimensionsIncludeLabels?: boolean;
  /**
   * whether to transition the node positions
   */
  animate?: boolean;
  /**
   * whether to animate specific nodes when animation is on; non-animated nodes immediately go to their final positions
   * @param node Instance of the Node to filter for
   * @param i Index number of the node in the sequence
   */
  animateFilter?: (node: any, i: number) => boolean;
  /**
   * duration of animation in ms if enabled
   */
  animationDuration?: number;
  /**
   * easing of animation if enabled
   * Note: This is wrong. This is actually a string, but Cytoscape typings are GARBAGE
   */
  animationEasing?: number;
  /**
   * constrain layout bounds; { x1, y1, x2, y2 } or { x1, y1, w, h }
   */
  boundingBox?: DagreBoundingBox;
  /**
   * a function that applies a transform to the final node position
   * @param node Instance of the Node to transform position for
   * @param pos Current position for the Node
   */
  transform?: (node: any, pos: DagrePosition) => DagrePosition;
  /**
   * On layout ready
   */
  ready?: () => void;
  /**
   * On layout stop
   */
  stop?: () => void;
}
