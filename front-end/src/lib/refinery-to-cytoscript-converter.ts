import {
  ApiEndpointWorkflowState,
  ApiGatewayResponseWorkflowState, LambdaWorkflowState,
  RefineryProject, ScheduleTriggerWorkflowState, SnsTopicWorkflowState, SqsQueueWorkflow,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import cytoscape from 'cytoscape';
import {
  CssStyleDeclaration,
  EdgeDefinition,
  ElementsDefinition,
  NodeDefinition,
} from 'cytoscape';

const baseElementProperties = {
  // group: 'nodes' as ElementGroup,
  // locked: true,
  grabbable: false
};

function basicConverter<T extends WorkflowState>(workflowState: WorkflowState, classname: string): NodeDefinition {
  const convertedState = workflowState as T;
  
  return {
    ...baseElementProperties,
    data: {
      name: convertedState.name,
      id: convertedState.id
    },
    // Holy crap these type definitions have a typo lol
    // @ts-ignore
    scratch: {
      _rawData: convertedState,
      _blockType: convertedState.type
    },
    // This is used by Cytoscape to render the image/style for each node
    // This should accept an array too, but I don't want to fight the type definitions today
    classes: classname
  };
}

function classOnlyConverter<T extends WorkflowState>(classname: string): (e: WorkflowState) => NodeDefinition {
  return e => basicConverter(e, classname);
}

export type WorkflowStateTypeConverterLookup = {
  [key: string]: (w: WorkflowState) => NodeDefinition
};

/**
 * Lookup table that maps the enum type for each workflow state to a function that then returns the Cytoscape-specific
 * configuration format.
 */
export const workflowStateTypeToConverter: WorkflowStateTypeConverterLookup = {
  [WorkflowStateType.API_ENDPOINT]: classOnlyConverter<ApiEndpointWorkflowState>(WorkflowStateType.API_ENDPOINT),
  [WorkflowStateType.API_GATEWAY_RESPONSE]: classOnlyConverter<ApiGatewayResponseWorkflowState>(WorkflowStateType.API_GATEWAY_RESPONSE),
  [WorkflowStateType.LAMBDA]: classOnlyConverter<LambdaWorkflowState>(WorkflowStateType.LAMBDA),
  [WorkflowStateType.SCHEDULE_TRIGGER]: classOnlyConverter<ScheduleTriggerWorkflowState>(WorkflowStateType.SCHEDULE_TRIGGER),
  [WorkflowStateType.SNS_TOPIC]: classOnlyConverter<SnsTopicWorkflowState>(WorkflowStateType.SNS_TOPIC),
  [WorkflowStateType.SQS_QUEUE]: classOnlyConverter<SqsQueueWorkflow>(WorkflowStateType.SQS_QUEUE)
};

export function generateCytoscapeElements(project: RefineryProject): ElementsDefinition {
  // Creates the "nodes" on the graph in Cytoscape format
  // http://js.cytoscape.org/#notation/elements-json
  const nodes = project.workflow_states.map(workflowState => {
    if (!workflowStateTypeToConverter[workflowState.type]) {
      const error = new Error('Unknown type to convert when mapping project to graph types');
      console.error(error, workflowState);
      throw error;
    }
    
    return workflowStateTypeToConverter[workflowState.type](workflowState);
  });
  
  const edges: EdgeDefinition[] = project.workflow_relationships.map(edge => {
    if (!edge) {
      const error = new Error('Unknown type to convert when mapping project to graph edges');
      console.error(error, edge);
      throw error;
    }
    
    // Cytoscape edge format
    // http://js.cytoscape.org/#notation/elements-json
    return {
      data: {
        // id: edge.id,
        name: edge.type as string,
        source: edge.node,
        target: edge.next
      }
    };
  });
  
  return {
    nodes,
    edges
  };
}

const baseNodeStyle = {
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

const baseEdgeStyle = {
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

type CytoscapeStyleConfigLookup = {
  [key: string]: {}
}

const cytoscapeConfigLookup: CytoscapeStyleConfigLookup = {
  [WorkflowStateType.API_ENDPOINT]: {
    'background-image': require('../../public/img/node-icons/api-gateway.png')
  },
  [WorkflowStateType.API_GATEWAY_RESPONSE]: {
    'background-image': require('../../public/img/node-icons/api-gateway.png')
  },
  [WorkflowStateType.LAMBDA]: {
    'background-image': require('../../public/img/node-icons/code-icon.png')
  },
  [WorkflowStateType.SCHEDULE_TRIGGER]: {
    'background-image': require('../../public/img/node-icons/clock-icon.png')
  },
  [WorkflowStateType.SNS_TOPIC]: {
    'background-image': require('../../public/img/node-icons/sns-topic.png')
  },
  [WorkflowStateType.SQS_QUEUE]: {
    'background-image': require('../../public/img/node-icons/sqs_queue.png')
  },
};

export function generateCytoscapeStyle(): CssStyleDeclaration {
  
  // Generate styles for each node
  const filledStyleHelper = Object.keys(cytoscapeConfigLookup).map(
    key => ({
      // CSS-style syntax
      selector: `.${key}`,
      style: cytoscapeConfigLookup[key]
    })
  );
  
  return [
    baseNodeStyle,
    baseEdgeStyle,
    ...filledStyleHelper
  ];
}

export function convertRefineryProjectToCytoscape(project: RefineryProject): cytoscape.CytoscapeOptions {
  return {
    elements: generateCytoscapeElements(project),
    // Per spec here: http://js.cytoscape.org/#style
    style: generateCytoscapeStyle()
  };
}
