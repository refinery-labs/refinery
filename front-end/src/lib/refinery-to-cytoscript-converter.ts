import {
  ApiEndpointWorkflowState,
  ApiGatewayResponseWorkflowState,
  LambdaWorkflowState,
  RefineryProject,
  ScheduleTriggerWorkflowState,
  SnsTopicWorkflowState,
  SqsQueueWorkflowState,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import cytoscape from 'cytoscape';
import { CssStyleDeclaration, EdgeDefinition, ElementsDefinition, NodeDefinition } from 'cytoscape';
import { baseEdgeStyle, baseNodeStyle } from '@/lib/cytoscape-styles';

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
  [key in WorkflowStateType]: ((w: WorkflowState) => NodeDefinition) | null
};

/**
 * Lookup table that maps the enum type for each workflow state to a function that then returns the Cytoscape-specific
 * configuration format.
 */
export const workflowStateTypeToConverter: WorkflowStateTypeConverterLookup = {
  [WorkflowStateType.API_ENDPOINT]: classOnlyConverter<ApiEndpointWorkflowState>(WorkflowStateType.API_ENDPOINT),
  [WorkflowStateType.API_GATEWAY_RESPONSE]: classOnlyConverter<ApiGatewayResponseWorkflowState>(
    WorkflowStateType.API_GATEWAY_RESPONSE
  ),
  [WorkflowStateType.LAMBDA]: classOnlyConverter<LambdaWorkflowState>(WorkflowStateType.LAMBDA),
  [WorkflowStateType.SCHEDULE_TRIGGER]: classOnlyConverter<ScheduleTriggerWorkflowState>(
    WorkflowStateType.SCHEDULE_TRIGGER
  ),
  [WorkflowStateType.SNS_TOPIC]: classOnlyConverter<SnsTopicWorkflowState>(WorkflowStateType.SNS_TOPIC),
  [WorkflowStateType.SQS_QUEUE]: classOnlyConverter<SqsQueueWorkflowState>(WorkflowStateType.SQS_QUEUE),
  [WorkflowStateType.API_GATEWAY]: null,
  [WorkflowStateType.WARMER_TRIGGER]: null
};

export function generateCytoscapeElements(project: RefineryProject): ElementsDefinition {
  // Creates the "nodes" on the graph in Cytoscape format
  // http://js.cytoscape.org/#notation/elements-json
  const nodes = project.workflow_states.map(workflowState => {
    if (Object.keys(workflowStateTypeToConverter).indexOf(workflowState.type) === -1) {
      const error = new Error('Unknown type to convert when mapping project to graph types');
      console.error(error, workflowState);
      throw error;
    }

    const converter = workflowStateTypeToConverter[workflowState.type];

    // Some types do not map to anything.
    if (!converter) {
      return null;
    }

    return converter(workflowState);
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
        id: edge.id,
        name: edge.type as string,
        source: edge.node,
        target: edge.next
      }
    };
  });

  // Ensure that there are not any null blocks
  const filteredNodes = nodes.filter(t => t !== null) as NodeDefinition[];

  return {
    nodes: filteredNodes,
    edges
  };
}

type CytoscapeStyleConfigLookup = {
  [key: string]: {};
};

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
  }
};

export function generateCytoscapeStyle(stylesheetOverrides?: CssStyleDeclaration): CssStyleDeclaration {
  // Generate styles for each node
  const filledStyleHelper = Object.keys(cytoscapeConfigLookup).map(key => ({
    // CSS-style syntax
    selector: `.${key}`,
    style: cytoscapeConfigLookup[key]
  }));

  return [baseNodeStyle, baseEdgeStyle, ...filledStyleHelper, ...stylesheetOverrides];
}

export function convertRefineryProjectToCytoscape(project: RefineryProject): cytoscape.CytoscapeOptions {
  return {
    elements: generateCytoscapeElements(project),
    // Per spec here: http://js.cytoscape.org/#style
    style: generateCytoscapeStyle()
  };
}
