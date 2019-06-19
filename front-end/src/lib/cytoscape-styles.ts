import { CollectionReturnValue, EventObject, SingularAnimationOptionsPos } from 'cytoscape';

export enum STYLE_CLASSES {
  SELECTED = 'selected',
  HIGHLIGHT = 'highlight',
  SELECTION_ANIMATION_ENABLED = 'selection-animation-enabled',
  DISABLED = 'disabled',
  EXECUTION_SUCCESS = 'execution-success',
  EXECUTION_CAUGHT = 'execution-caught',
  EXECUTION_FAILURE = 'execution-failure'
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
    'target-endpoint': 'outside-to-node-or-label'
  }
};

/*
 * Imported by default (global styles)
 */
export const baseCytoscapeStyles = [
  {
    selector: `node.${STYLE_CLASSES.HIGHLIGHT}`,
    style: {
      // 'background-blacken': -0.2,
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
      'target-arrow-color': '#6391dd'
    }
  },
  {
    selector: 'node.disabled',
    style: {
      'background-blacken': 0.4,
      opacity: '0.8'
    }
  },
  {
    selector: 'edge.disabled',
    style: {
      'line-color': '#59729e',
      'target-arrow-color': '#59729e'
    }
  },
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
  },
  {
    selector: `node.${STYLE_CLASSES.EXECUTION_SUCCESS}`,
    style: {
      'background-image': require('../../public/img/node-icons/code-block-success.png')
    }
  },
  {
    selector: `node.${STYLE_CLASSES.EXECUTION_CAUGHT}`,
    style: {
      'background-image': require('../../public/img/node-icons/code-block-caught.png')
    }
  },
  {
    selector: `node.${STYLE_CLASSES.EXECUTION_FAILURE}`,
    style: {
      'background-image': require('../../public/img/node-icons/code-block-error.png')
    }
  }
  // {
  //   selector: `node.${STYLE_CLASSES.SELECTION_ANIMATION_ENABLED}`,
  //   style: {
  //     'border-width': '4px',
  //     'border-color': 'red'
  //   }
  // }
];

// Bad type declarations bite again!
// @ts-ignore
export const animationBegin: SingularAnimationOptionsPos = {
  style: {
    opacity: '0.7',
    'background-blacken': -0.6
  },
  duration: 600,
  easing: 'ease-in-sine'
};

// @ts-ignore
export const animationEnd: SingularAnimationOptionsPos = {
  style: {
    opacity: '1',
    'background-blacken': 0
  },
  duration: 600,
  easing: 'ease-in-sine'
};

export const selectableAnimation = async (ele: CollectionReturnValue): Promise<EventObject> => {
  return (
    // Annoying bad type declarations...
    // @ts-ignore
    ele
      .animate(animationBegin)
      .delay(600)
      .animate(animationEnd, {
        complete(): void {
          selectableAnimation(ele);
        }
      })
      .delay(600)
  );
};
