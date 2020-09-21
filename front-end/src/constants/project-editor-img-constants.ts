// A little bit of impedance mismatch going on, unfortunately.
import { WorkflowStateType } from '@/types/graph';
import { BlockSelectionType, BlockTypeConfig } from '@/constants/project-editor-constants';

export const blockTypeToImageLookup: BlockTypeConfig = {
  [WorkflowStateType.API_ENDPOINT]: {
    path: require('../../public/img/node-icons/api-gateway.png'),
    name: 'API Endpoint Block',
    description:
      'Creates a web endpoint and passes web request data to the connected Code Block. ' +
      'Must be used with an API Response block to return a web response.'
  },
  [WorkflowStateType.API_GATEWAY]: {
    path: require('../../public/img/node-icons/api-gateway.png'),
    name: 'API Gateway Block',
    description: 'Why do you see this? Please report!'
  },
  [WorkflowStateType.API_GATEWAY]: {
    path: require('../../public/img/node-icons/api-gateway.png'),
    name: 'API Gateway Block',
    description: 'Why do you see this? Please report!'
  },
  [WorkflowStateType.WARMER_TRIGGER]: {
    path: require('../../public/img/node-icons/api-gateway.png'),
    name: 'Warmer Trigger',
    description: 'Why do you see this? Please report!'
  },
  [WorkflowStateType.API_GATEWAY_RESPONSE]: {
    path: require('../../public/img/node-icons/api-gateway.png'),
    name: 'API Endpoint Response Block',
    description:
      'Returns the output from a Code Block to the web request started by the API Endpoint block. ' +
      'Must be downstream from an API Endpoint block, ' +
      'responses which take over 29 seconds will time out the API Endpoint response.'
  },
  [WorkflowStateType.LAMBDA]: {
    path: require('../../public/img/node-icons/code-icon.png'),
    name: 'Code Block',
    description:
      'Runs a user-defined script in PHP/Python/Node/Go. ' +
      'Takes output from a previous block as input to the script and returns the result returned from it.'
  },
  [WorkflowStateType.SCHEDULE_TRIGGER]: {
    path: require('../../public/img/node-icons/clock-icon.png'),
    name: 'Timer Block',
    description:
      'Runs blocks connected to it on a user-specified schedule. ' +
      'For example, run a block every minute or run a workflow every day at 3:00 PM.'
  },
  [WorkflowStateType.SNS_TOPIC]: {
    path: require('../../public/img/node-icons/sns-topic.png'),
    name: 'Topic Block',
    description:
      'Concurrently executes all Code Blocks connected to it and passes the input to the connected ' +
      'blocks. For example, take some input data and then immediately execute three Code blocks with that input.'
  },
  [WorkflowStateType.SQS_QUEUE]: {
    path: require('../../public/img/node-icons/sqs_queue.png'),
    name: 'Queue Block',
    description:
      'Takes input items to process and sends them to the connected Code Block. ' +
      'This block will automatically increase concurrent executions of the connected Code Block until ' +
      'either the concurrency ceiling is hit or the queue empties.'
  },
  [WorkflowStateType.SQS_QUEUE_HANDLER]: {
    path: require('../../public/img/node-icons/sqs_queue.png'),
    name: 'Queue Handler Block',
    description: 'Why do you see this? Please report!'
  },
  [BlockSelectionType.saved_block]: {
    path: require('../../public/img/node-icons/code-icon.png'),
    name: 'Saved Block / Community Repository Block',
    description:
      'Import a previously created Saved Block into your current project. This can be a Saved Block you created or any of the Saved Blocks publicly published by other Refinery users.'
  }
};
