import cytoscape from '@/components/CytoscapeGraph';

// Annoying that these both have to be ts-ignore'd because `stylesheet` isn't defined by Cytoscape's definitions
// @ts-ignore
const getStyleImage = ele => require('../../public/img/node-icons/code-icon.png');

// @ts-ignore
const cytoscapeStyle = cytoscape.stylesheet()
  .selector('node').style({
    width: 64,
    height: 64,
    shape: 'roundrectangle',
    'background-fit': 'contain',
    'background-color': '#fff',
    'background-image': require('../../public/img/node-icons/code-icon.png')
  })
  .selector('edge').style({
      'width': 5,
      'target-arrow-shape': 'triangle',
      'line-color': '#9dbaea',
      'target-arrow-color': '#9dbaea',
      'curve-style': 'bezier',
      'label': 'asdf',
      color: '#444',
      'text-margin-x ': '50px'
    }
  );

const cytoscapeConfig: cytoscape.CytoscapeOptions = {
  layout: {
    name: 'dagre',
    nodeDimensionsIncludeLabels: true,
    animate: true,
    // animationEasing: 'cubic',
    spacingFactor: 1.2
  },
  
  boxSelectionEnabled: false,
  autounselectify: true,
  
  style: cytoscapeStyle,
  
  elements: {
    nodes: [
      { data: { id: 'n0' } },
      { data: { id: 'n1' } },
      { data: { id: 'n2' } },
      { data: { id: 'n3' } },
      { data: { id: 'n4' } },
      { data: { id: 'n5' } },
      { data: { id: 'n6' } },
      { data: { id: 'n7' } },
      { data: { id: 'n8' } },
      { data: { id: 'n9' } },
      { data: { id: 'n10' } },
      { data: { id: 'n11' } },
      { data: { id: 'n12' } },
      { data: { id: 'n13' } },
      { data: { id: 'n14' } },
      { data: { id: 'n15' } },
      { data: { id: 'n16' } }
    ],
    edges: [
      { data: { source: 'n0', target: 'n1' } },
      { data: { source: 'n0', target: 'n1' } },
      { data: { source: 'n1', target: 'n2' } },
      { data: { source: 'n1', target: 'n3' } },
      { data: { source: 'n4', target: 'n5' } },
      { data: { source: 'n4', target: 'n6' } },
      { data: { source: 'n6', target: 'n7' } },
      { data: { source: 'n6', target: 'n8' } },
      { data: { source: 'n8', target: 'n9' } },
      { data: { source: 'n8', target: 'n10' } },
      { data: { source: 'n11', target: 'n12' } },
      { data: { source: 'n12', target: 'n13' } },
      { data: { source: 'n13', target: 'n14' } },
      { data: { source: 'n13', target: 'n15' } },
    ]
  }
};
