import { DagreLayout } from './layout';

// registers the extension on a cytoscape lib ref
export function registerCustomDagre(cytoscape: (extensionName: string, foo: string, bar: any) => cytoscape.Core) {
  // can't register if cytoscape unspecified
  if (!cytoscape) {
    throw new Error('Unable to register dagre due to missing Cytoscape instance');
  }

  cytoscape('layout', 'dagre', DagreLayout); // register with cytoscape.js
}
