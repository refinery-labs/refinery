
export enum STYLE_CLASSES {
  SELECTED = 'selected',
  HIGHLIGHT = 'highlight'
}

/*
 * Explicitly defined by nodes themselves
 */
export const baseNodeStyle = {
  selector: 'node',
  style: {
    width: 64,
    height: 64,
    shape: 'roundrectangle',
    label: 'data(name)',
    color: '#fff',
    'background-fit': 'contain',
    'background-color': '#fff',
    'text-valign': 'bottom',
    'compound-sizing-wrt-labels': 'include',
    'text-margin-y': '6px',
    'text-background-color': '#000',
    'text-background-opacity': '0.5',
    'text-background-padding': '4px',
    'text-background-shape': 'roundrectangle'
  }
};

export const baseEdgeStyle = {
  selector: 'edge',
  style: {
    width: 5,
    label: 'data(name)',
    color: '#2a2a2a',
    'target-arrow-shape': 'triangle',
    'line-color': '#9dbaea',
    'target-arrow-color': '#9dbaea',
    'curve-style': 'bezier',
    'text-rotation': 'autorotate',
    'target-endpoint': 'outside-to-node-or-label',
  }
};

/*
 * Imported by default (global styles)
 */
export const baseCytoscapeStyles = [
  {
    selector: `node.${STYLE_CLASSES.HIGHLIGHT}`,
    style: {
      'background-blacken': -0.2,
      color: '#fff',
      'text-background-color': '#333'
    }
  },
  {
    selector: 'edge.highlight',
    style: {
      'mid-target-arrow-color': '#FFF',
      color: '#3f3f3f',
      'line-color': '#6391dd',
      'target-arrow-color': '#6391dd',
    }
  },
  // Used for a 'fade out' effect on mouseover, but honestly looks bad.
  // {
  //   selector: 'node.semitransp',
  //   style:{ 'opacity': '0.95' }
  // },
  // {
  //   selector: 'edge.semitransp',
  //   style:{ 'opacity': '0.95' }
  // },
  {
    selector: `node.${STYLE_CLASSES.SELECTED}`,
    style: {
      'border-width': '4px',
      'border-color': 'red'
    }
  },
  {
    selector: `edge.${STYLE_CLASSES.SELECTED}`,
    style: {
      'line-color': '#ff4444',
      'target-arrow-color': '#ff4444',
      color: '#000'
    }
  }
];
