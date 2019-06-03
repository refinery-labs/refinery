import {WorkflowRelationshipType, WorkflowStateType} from '@/types/graph';
import {ActiveSidebarPaneToContainerMapping, SIDEBAR_PANE} from '@/types/project-editor-types';
import AddBlockPane from '@/components/ProjectEditor/AddBlockPane';
import AddTransitionPane from '@/components/ProjectEditor/AddTransitionPane';

export const BlockSelectionType = {
  ...WorkflowStateType,
  saved_lambda: 'saved_lambda'
};

export interface AddGraphElementConfig {
  // TODO: Add images for Transitions
  path?: string;
  name: string;
  description: string;
}

export type BlockTypeToImage = {
  [key in WorkflowStateType]: AddGraphElementConfig;
}

export interface BlockTypeConfig extends BlockTypeToImage {
  [index:string]: AddGraphElementConfig;
  saved_lambda: AddGraphElementConfig;
}

// A little bit of impedance mismatch going on, unfortunately.
export const blockTypeToImageLookup: BlockTypeConfig = {
  [WorkflowStateType.API_ENDPOINT]: {
    path: require('../../public/img/node-icons/api-gateway.png'),
    name: 'API Endpoint Block',
    description: 'Creates a web endpoint and passes web request data to the connected Lambda Block. ' +
      'Must be used with an API Response block to return a web response.'
  },
  [WorkflowStateType.API_GATEWAY]: {
    path: require('../../public/img/node-icons/api-gateway.png'),
    name: 'API Gateway Block',
    description: 'Why do you see this? Please report!'
  },
  [WorkflowStateType.API_GATEWAY_RESPONSE]: {
    path: require('../../public/img/node-icons/api-gateway.png'),
    name: 'API Gateway Response Block',
    description: 'Returns the output from a Lambda Block to the web request started by the API Endpoint block. ' +
      'Must be downstream from an API Endpoint block, ' +
      'responses which take over 29 seconds will time out the API Endpoint response.'
  },
  [WorkflowStateType.LAMBDA]: {
    path: require('../../public/img/node-icons/code-icon.png'),
    name: 'Code Block',
    description: 'Runs a user-defined script in PHP/Python/Node. ' +
      'Takes output from a previous block as input to the script and returns the result returned from it.'
  },
  [WorkflowStateType.SCHEDULE_TRIGGER]: {
    path: require('../../public/img/node-icons/clock-icon.png'),
    name: 'Timer Block',
    description: 'Runs blocks connected to it on a user-specified schedule. ' +
      'For example, run a block every minute or run a workflow every day at 3:00 PM.'
  },
  [WorkflowStateType.SNS_TOPIC]: {
    path: require('../../public/img/node-icons/sns-topic.png'),
    name: 'Topic Block',
    description: 'Concurrently executes all Lambda Blocks connected to it and passes the input to the connected ' +
      'blocks. For example, take some input data and then immediately execute three Lambda blocks with that input.'
  },
  [WorkflowStateType.SQS_QUEUE]: {
    path: require('../../public/img/node-icons/sqs_queue.png'),
    name: 'Queue Block',
    description: 'Takes input items to process and sends them to the connected Lambda Block. ' +
      'This block will automatically increase concurrent executions of the connected Lambda Block until ' +
      'either the concurrency ceiling is hit or the queue empties.'
  },
  saved_lambda: {
    path: require('../../public/img/node-icons/code-icon.png'),
    name: 'Saved Code Block',
    description: 'Adds a previously-saved Lambda block to the workflow.'
  }
};

export const availableBlocks: string[] = [
  WorkflowStateType.LAMBDA,
  BlockSelectionType.saved_lambda,
  WorkflowStateType.SCHEDULE_TRIGGER,
  WorkflowStateType.API_ENDPOINT,
  WorkflowStateType.SNS_TOPIC,
  WorkflowStateType.SQS_QUEUE
];

export type TransitionTypeToConfig = {
  [key in WorkflowRelationshipType]: AddGraphElementConfig;
}

export const transitionTypeToConfigLookup: TransitionTypeToConfig = {
  [WorkflowRelationshipType.IF]: {
    name: 'If Transition',
    description: 'Runs another block if the returSearchSavedProjectsResultned data from the first block matches the specified conditional. ' +
      'For example, if the output of a block equals “success” run the next block.'
  },
  [WorkflowRelationshipType.THEN]: {
    name: 'Then Transition',
    description: 'Takes input from a block and passes it to another block. This transition will ' +
      'always occur unless the first block is a Code Block which has thrown an uncaught exception (failed).'
  },
  [WorkflowRelationshipType.ELSE]: {
    name: 'Else Transition',
    description: 'A transition which will run if no other transitions are taken. For example, the “if” transition ' +
      'required the output of the first block be “success” and the preceding block returns “failed” then the ' +
      'block connected via the “else” transition would be run.'
  },
  [WorkflowRelationshipType.EXCEPTION]: {
    name: 'Code Exception Transition',
    description: 'Runs another block only if the preceding Code Block encountered an uncaught exception. ' +
      'For example, run this block to send an email notification if a Code Block errors out.'
  },
  [WorkflowRelationshipType.FAN_IN]: {
    name: 'Fan In Transition',
    description: 'A “fan-in” transition takes the returned values of all of the Code Blocks executed from a ' +
      '“fan-out”, turns them into an array, and then passes them all as input to a single connected Code Block. ' +
      'Sister-transition to the “fan-out” transition and can only be used downstream from a ' +
      'fan-out transition in a workflow.'
  },
  [WorkflowRelationshipType.FAN_OUT]: {
    name: 'Fan Out Transition',
    description: 'Runs the connected Code Block for every item in the array returned from the preceding Code Block. ' +
      'For example, if you return [1,2,3] from a Code Block then three Code Blocks will be run ' +
      'with “1”, “2”, “3” as input respectively.'
  }
};

export const availableTransitions = [
  WorkflowRelationshipType.IF,
  WorkflowRelationshipType.THEN,
  WorkflowRelationshipType.ELSE,
  WorkflowRelationshipType.EXCEPTION,
  WorkflowRelationshipType.FAN_IN,
  WorkflowRelationshipType.FAN_OUT
];

export interface ValidTransitionConfig {
  fromType: WorkflowStateType,
  toType: WorkflowStateType
}

export const validBlockToBlockTransitionLookup: ValidTransitionConfig[] = [
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.LAMBDA,
  },
  {
    fromType: WorkflowStateType.SQS_QUEUE,
    toType: WorkflowStateType.LAMBDA,
  },
  {
    fromType: WorkflowStateType.SCHEDULE_TRIGGER,
    toType: WorkflowStateType.LAMBDA,
  },
  {
    fromType: WorkflowStateType.SNS_TOPIC,
    toType: WorkflowStateType.LAMBDA,
  },
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.SNS_TOPIC,
  },
  {
    fromType: WorkflowStateType.API_ENDPOINT,
    toType: WorkflowStateType.LAMBDA,
  },
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.API_GATEWAY_RESPONSE,
  }
];

/**
 * Allow only "Then" transitions for these cases
 */
export const nodeTypesWithSimpleTransitions: ValidTransitionConfig[] = [
  {
    fromType: WorkflowStateType.SCHEDULE_TRIGGER,
    toType: WorkflowStateType.LAMBDA
  },
  {
    fromType: WorkflowStateType.SQS_QUEUE,
    toType: WorkflowStateType.LAMBDA,
  },
  {
    fromType: WorkflowStateType.SNS_TOPIC,
    toType: WorkflowStateType.LAMBDA,
  },
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.SNS_TOPIC,
  },
  {
    fromType: WorkflowStateType.API_ENDPOINT,
    toType: WorkflowStateType.LAMBDA,
  },
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.API_GATEWAY_RESPONSE,
  }
];

export const DEFAULT_PROJECT_CONFIG = {
  "version": "1.0.0",
  /*
    {
      {{node_id}}: [
        {
          "key": "value"
        }
      ]
    }
  */
  "environment_variables": {},
  /*
    {
      "api_gateway_id": {{api_gateway_id}}
    }
  */
  "api_gateway": {
    "gateway_id": false,
  },
  
  "logging": {
    "level": "LOG_ALL",
  }
};

export const paneToContainerMapping: ActiveSidebarPaneToContainerMapping = {
  [SIDEBAR_PANE.addBlock]: AddBlockPane,
  [SIDEBAR_PANE.addTransition]: AddTransitionPane,
  [SIDEBAR_PANE.allBlocks]: AddBlockPane,
  [SIDEBAR_PANE.allVersions]: AddBlockPane,
  [SIDEBAR_PANE.deployProject]: AddBlockPane,
  [SIDEBAR_PANE.saveProject]: AddBlockPane,
  [SIDEBAR_PANE.editBlock]: AddBlockPane,
  [SIDEBAR_PANE.editTransition]: AddBlockPane
};
