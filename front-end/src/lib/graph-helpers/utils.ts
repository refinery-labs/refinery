import { Graph } from 'graphlib';

function getGraphSuccessors(graph: Graph, root: string): string[] {
  const successors = graph.successors(root);
  if (successors) {
    return successors;
  }
  return [];
}

export function recursiveSuccessorMark(graph: Graph, root: string, markedNodes: string[]) {
  // Get the successors from the root node
  const successors = getGraphSuccessors(graph, root);

  // Unmarked nodes are ones that we have not seen yet
  const unmarkedNodes = successors.filter(n => !markedNodes.includes(n));
  markedNodes = [...markedNodes, ...unmarkedNodes];

  // For every unmarked node, get its marked nodes
  unmarkedNodes.forEach(n => {
    const successorMarkedNodes = recursiveSuccessorMark(graph, n, markedNodes);
    const successorFoundMarkedNodes = successorMarkedNodes.filter(n => !markedNodes.includes(n));
    markedNodes = [...markedNodes, ...successorFoundMarkedNodes];
  });
  return markedNodes;
}

export function addCytoscapeElementsToShadowGraph(
  graph: Graph,
  nodes: cytoscape.NodeDefinition[],
  edges: cytoscape.EdgeDefinition[]
): Graph {
  nodes.forEach(node => {
    graph.setNode(node.data.id ? node.data.id : '');
  });

  edges.forEach(edge => {
    graph.setEdge(edge.data.source, edge.data.target, {}, edge.data.id);
  });

  return graph;
}
