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
  ElementGroup,
  ElementsDefinition,
  NodeDefinition,
} from 'cytoscape';
import StylesheetHelper = cytoscape.StylesheetHelper;

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
  width: 64,
  height: 64,
  shape: 'roundrectangle',
  label: 'data(name)',
  'background-fit': 'contain',
  'background-color': '#fff'
};

const baseEdgeStyle = {
  width: 5,
  label: 'data(name)',
  color: '#444',
  'target-arrow-shape': 'triangle',
  'line-color': '#9dbaea',
  'target-arrow-color': '#9dbaea',
  'curve-style': 'bezier',
  'text-margin-x ': '50px'
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

  // TODO: Wait until the stylesheet types are landed.
  // @ts-ignore
  const cytoscapeStyleHelper = cytoscape.stylesheet() as StylesheetHelper;
  
  cytoscapeStyleHelper.selector('node').style(baseNodeStyle);
  cytoscapeStyleHelper.selector('edge').style(baseEdgeStyle);
  
  // Black magic, I know.
  // This will apply each "style" against the StyleHelper and then return the helper at the end.
  const filledStyleHellper = Object.keys(cytoscapeConfigLookup).reduce(
    (out, key) => out.selector(`.${key}`).style(cytoscapeConfigLookup[key]),
    cytoscapeStyleHelper
  );
  
  return filledStyleHellper as CssStyleDeclaration;
}

export function convertRefineryProjectToCytoscape(project: RefineryProject): cytoscape.CytoscapeOptions {
  return {
    elements: generateCytoscapeElements(project),
    // Per spec here: http://js.cytoscape.org/#style
    style: generateCytoscapeStyle()
  };
}
