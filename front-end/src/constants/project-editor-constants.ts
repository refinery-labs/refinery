import {
  ApiEndpointWorkflowState,
  ApiGatewayResponseWorkflowState,
  LambdaWorkflowState,
  ScheduleTriggerWorkflowState,
  SnsTopicWorkflowState,
  SqsQueueWorkflowState,
  SupportedLanguage,
  WorkflowRelationshipType,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { ActiveSidebarPaneToContainerMapping, SIDEBAR_PANE } from '@/types/project-editor-types';
import AddBlockPane from '@/components/ProjectEditor/AddBlockPane';
import AddTransitionPane from '@/components/ProjectEditor/AddTransitionPane';
import EditBlockPane from '@/components/ProjectEditor/EditBlockPane';
import { HTTP_METHOD } from '@/constants/api-constants';
import DeployProjectPane from '@/components/ProjectEditor/DeployProjectPane';
import ExportProjectPane from '@/components/ProjectEditor/ExportProjectPane';
import ViewApiEndpointsPane from '@/components/DeploymentViewer/ViewApiEndpointsPane';
import ViewExecutionsPane from '@/components/DeploymentViewer/ViewExecutionsPane';
import ViewDeployedBlockPane from '@/components/DeploymentViewer/ViewDeployedBlockPane';
import ViewDeployedTransitionPane from '@/components/DeploymentViewer/ViewDeployedTransitionPane';
import DestroyDeploymentPane from '@/components/DeploymentViewer/DestroyDeploymentPane';
import { VueConstructor } from 'vue';
import { EditLambdaBlock } from '@/components/ProjectEditor/block-components/EditLambdaBlockPane';
import { EditAPIEndpointBlock } from '@/components/ProjectEditor/block-components/EditAPIEndpointBlockPane';
import { EditQueueBlock } from '@/components/ProjectEditor/block-components/EditQueuePane';
import { EditAPIResponseBlock } from '@/components/ProjectEditor/block-components/EditAPIResponseBlockPane';
import { EditScheduleTriggerBlock } from '@/components/ProjectEditor/block-components/EditScheduleTriggerBlockPane';
import { EditTopicBlock } from '@/components/ProjectEditor/block-components/EditTopicBlockPane';
import RunEditorCodeBlockPane from '@/components/ProjectEditor/RunEditorCodeBlockPane';
import EditTransitionPane from '@/components/ProjectEditor/EditTransitionPane';
import RunDeployedCodeBlockPane from '@/components/DeploymentViewer/RunDeployedCodeBlockPane';
import ViewDeployedBlockLogsPane from '@/components/DeploymentViewer/ViewDeployedBlockLogsPane';
import generateStupidName from '@/lib/silly-names';
import AddSavedBlockPane from '@/components/ProjectEditor/AddSavedBlockPane';

export const savedBlockType = 'saved_block';

export const BlockSelectionType = {
  ...WorkflowStateType,
  saved_block: savedBlockType
};

export interface AddGraphElementConfig {
  // TODO: Add images for Transitions
  path?: string;
  name: string;
  description: string;
}

export type BlockTypeToImage = { [key in WorkflowStateType]: AddGraphElementConfig };

export interface BlockTypeConfig extends BlockTypeToImage {
  [index: string]: AddGraphElementConfig;
  // saved_lambda: AddGraphElementConfig;
}

// A little bit of impedance mismatch going on, unfortunately.
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
  [BlockSelectionType.saved_block]: {
    path: require('../../public/img/node-icons/code-icon.png'),
    name: 'Saved Block',
    description: 'Choose a previously saved block to add to the project graph.'
  }
};

export const availableBlocks: string[] = [
  WorkflowStateType.LAMBDA,
  BlockSelectionType.saved_block,
  WorkflowStateType.SCHEDULE_TRIGGER,
  WorkflowStateType.API_ENDPOINT,
  WorkflowStateType.SNS_TOPIC,
  WorkflowStateType.SQS_QUEUE
];

export type TransitionTypeToConfig = { [key in WorkflowRelationshipType]: AddGraphElementConfig };

export const transitionTypeToConfigLookup: TransitionTypeToConfig = {
  [WorkflowRelationshipType.IF]: {
    name: 'If Transition',
    description:
      'Runs another block if the returned data from the first block matches the specified conditional. ' +
      'For example, if the output of a block equals “success” run the next block.'
  },
  [WorkflowRelationshipType.THEN]: {
    name: 'Then Transition',
    description:
      'Takes input from a block and passes it to another block. This transition will ' +
      'always occur unless the first block is a Code Block which has thrown an uncaught exception (failed).'
  },
  [WorkflowRelationshipType.ELSE]: {
    name: 'Else Transition',
    description:
      'A transition which will run if no other transitions are taken. For example, the “if” transition ' +
      'required the output of the first block be “success” and the preceding block returns “failed” then the ' +
      'block connected via the “else” transition would be run.'
  },
  [WorkflowRelationshipType.EXCEPTION]: {
    name: 'Code Exception Transition',
    description:
      'Runs another block only if the preceding Code Block encountered an uncaught exception. ' +
      'For example, run this block to send an email notification if a Code Block errors out.'
  },
  [WorkflowRelationshipType.FAN_IN]: {
    name: 'Fan In Transition',
    description:
      'A “fan-in” transition takes the returned values of all of the Code Blocks executed from a ' +
      '“fan-out”, turns them into an array, and then passes them all as input to a single connected Code Block. ' +
      'Sister-transition to the “fan-out” transition and can only be used downstream from a ' +
      'fan-out transition in a workflow.'
  },
  [WorkflowRelationshipType.FAN_OUT]: {
    name: 'Fan Out Transition',
    description:
      'Runs the connected Code Block for every item in the array returned from the preceding Code Block. ' +
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
  fromType: WorkflowStateType;
  toType: WorkflowStateType;
}

export const validBlockToBlockTransitionLookup: ValidTransitionConfig[] = [
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.LAMBDA
  },
  {
    fromType: WorkflowStateType.SQS_QUEUE,
    toType: WorkflowStateType.LAMBDA
  },
  {
    fromType: WorkflowStateType.SCHEDULE_TRIGGER,
    toType: WorkflowStateType.LAMBDA
  },
  {
    fromType: WorkflowStateType.SNS_TOPIC,
    toType: WorkflowStateType.LAMBDA
  },
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.SNS_TOPIC
  },
  {
    fromType: WorkflowStateType.API_ENDPOINT,
    toType: WorkflowStateType.LAMBDA
  },
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.API_GATEWAY_RESPONSE
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
    toType: WorkflowStateType.LAMBDA
  },
  {
    fromType: WorkflowStateType.SNS_TOPIC,
    toType: WorkflowStateType.LAMBDA
  },
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.SNS_TOPIC
  },
  {
    fromType: WorkflowStateType.API_ENDPOINT,
    toType: WorkflowStateType.LAMBDA
  },
  {
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.API_GATEWAY_RESPONSE
  }
];

export const DEFAULT_PROJECT_CONFIG = {
  version: '1.0.0',
  /*
    {
      {{node_id}}: [
        {
          "key": "value"
        }
      ]
    }
  */
  environment_variables: {},
  /*
    {
      "api_gateway_id": {{api_gateway_id}}
    }
  */
  api_gateway: {
    gateway_id: false
  },

  logging: {
    level: 'LOG_ALL'
  }
};

export type DefaultCodeFromLanguage = { [key in SupportedLanguage]: string };

export const DEFAULT_LANGUAGE_CODE: DefaultCodeFromLanguage = {
  [SupportedLanguage.PYTHON_2]: `
def main(block_input, backpack):
    return "Hello World!"
`,
  [SupportedLanguage.NODEJS_8]: `
async function main(blockInput, backpack) {
	return 'Hello World!';
}
`,
  [SupportedLanguage.PHP7]: `
<?php
// Uncomment if you specified libraries
// require __DIR__ . "/vendor/autoload.php";
function main($block_input, $backpack) {
	return 'Hello World!';
}
`,
  [SupportedLanguage.GO1_12]: `package main

import (
	// The following imports are required
	// by the Refinery runtime do not remove them!
	"os"
	"fmt"
	"bytes"
	"runtime"
	"encoding/json"
	// Add your imports below this line
)

// Modify BlockInput to conform to your input data schema
type BlockInput struct {
	Example string \`json:"example"\`
}

// Modify block_main() appropriately.
// It must return a JSON-serializable value
func block_main(block_input []byte, backpack []byte) (bool, []byte) {
	var unmarshalled_input BlockInput
	
	// lambda_input is a byte array of the input to this code block11
	// This is a JSON-serialized value returned from another block.
	json.Unmarshal(block_input, &unmarshalled_input)
	
	// backpack is a byte array of the backpack variable passed to this code block
	// You must return the backpack, modified or unchanged, as your secondary return value.
	// e.g: return return_value, backpack
	return false, backpack
}
`
};

const SHARED_BLOCK_DEFAULTS: WorkflowState = {
  id: 'YOU-SHOULD-NEVER-SEE-THIS',
  name: 'You Should Not Ever See This!',
  version: '1.0.0',
  // This is purposefully invalid
  // @ts-ignore
  type: 'unknown'
};

export const CODE_BLOCK_DEFAULT_STATE: LambdaWorkflowState = {
  ...SHARED_BLOCK_DEFAULTS,
  language: SupportedLanguage.PYTHON_2,
  code: DEFAULT_LANGUAGE_CODE[SupportedLanguage.PYTHON_2],
  memory: 768,
  libraries: [],
  layers: [],
  // Changing this to max allowed time by default because
  // that's likely what people would prefer
  max_execution_time: 900,
  type: WorkflowStateType.LAMBDA,
  environment_variables: {}
};

export const SCHEDULE_EXPRESSION_BLOCK_DEFAULT_STATE: ScheduleTriggerWorkflowState = {
  ...SHARED_BLOCK_DEFAULTS,
  description: 'Deployed by Refinery',
  input_string: '',
  schedule_expression: 'rate(2 minutes)',
  type: WorkflowStateType.SCHEDULE_TRIGGER
};

export const TOPIC_BLOCK_DEFAULT_STATE: SnsTopicWorkflowState = {
  ...SHARED_BLOCK_DEFAULTS,
  type: WorkflowStateType.SNS_TOPIC
};

export const QUEUE_BLOCK_DEFAULT_STATE: SqsQueueWorkflowState = {
  ...SHARED_BLOCK_DEFAULTS,
  batch_size: 1,
  type: WorkflowStateType.SQS_QUEUE
};

export const API_ENDPOINT_BLOCK_DEFAULT_STATE: ApiEndpointWorkflowState = {
  ...SHARED_BLOCK_DEFAULTS,
  api_path: '/',
  http_method: HTTP_METHOD.GET,
  type: WorkflowStateType.API_ENDPOINT
};

export const API_GATEWAY_RESPONSE_BLOCK_DEFAULT_STATE: ApiGatewayResponseWorkflowState = {
  ...SHARED_BLOCK_DEFAULTS,
  type: WorkflowStateType.API_GATEWAY_RESPONSE
};

export type BlockTypeToDefaultState = { [key in WorkflowStateType]: () => WorkflowState };

export const blockTypeToDefaultStateMapping: BlockTypeToDefaultState = {
  [WorkflowStateType.LAMBDA]: () => CODE_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.SQS_QUEUE]: () => QUEUE_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.API_GATEWAY_RESPONSE]: () => API_GATEWAY_RESPONSE_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.API_ENDPOINT]: () => ({
    ...API_ENDPOINT_BLOCK_DEFAULT_STATE,
    api_path: `/replaceme/${generateStupidName()
      .toLowerCase()
      .split(' ')
      .join('')}`
  }),
  [WorkflowStateType.SCHEDULE_TRIGGER]: () => SCHEDULE_EXPRESSION_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.SNS_TOPIC]: () => TOPIC_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.API_GATEWAY]: () => SHARED_BLOCK_DEFAULTS
};

export const paneToContainerMapping: ActiveSidebarPaneToContainerMapping = {
  [SIDEBAR_PANE.runEditorCodeBlock]: RunEditorCodeBlockPane,
  [SIDEBAR_PANE.runDeployedCodeBlock]: RunDeployedCodeBlockPane,
  [SIDEBAR_PANE.addBlock]: AddBlockPane,
  [SIDEBAR_PANE.addSavedBlock]: AddSavedBlockPane,
  [SIDEBAR_PANE.addTransition]: AddTransitionPane,
  [SIDEBAR_PANE.allBlocks]: AddBlockPane,
  [SIDEBAR_PANE.allVersions]: AddBlockPane,
  [SIDEBAR_PANE.exportProject]: ExportProjectPane,
  [SIDEBAR_PANE.deployProject]: DeployProjectPane,
  [SIDEBAR_PANE.saveProject]: AddBlockPane,
  [SIDEBAR_PANE.editBlock]: EditBlockPane,
  [SIDEBAR_PANE.editTransition]: EditTransitionPane,
  [SIDEBAR_PANE.viewApiEndpoints]: ViewApiEndpointsPane,
  [SIDEBAR_PANE.viewExecutions]: ViewExecutionsPane,
  [SIDEBAR_PANE.destroyDeploy]: DestroyDeploymentPane,
  [SIDEBAR_PANE.viewDeployedBlock]: ViewDeployedBlockPane,
  [SIDEBAR_PANE.viewDeployedBlockLogs]: ViewDeployedBlockLogsPane,
  [SIDEBAR_PANE.viewDeployedTransition]: ViewDeployedTransitionPane
};

export const blockNameText = 'Name of the block.';
export const returnDataText = 'Data returned from the Code.';
export const languagesText = 'Language of code block.';
export const importLibsText = 'Dependencies for the code.';
export const codeEditorText = 'Code to be executed by the block.';
export const maxExecutionTimeText = 'Maximum time the code may execute before being killed in seconds.';
export const maxExecutionMemoryText = 'Maximum memory for the code to use during execution.';

export type BlockTypeToEditorComponent = { [key in WorkflowStateType]: VueConstructor };

export const blockTypeToEditorComponentLookup: BlockTypeToEditorComponent = {
  [WorkflowStateType.LAMBDA]: EditLambdaBlock,
  [WorkflowStateType.SNS_TOPIC]: EditTopicBlock,
  [WorkflowStateType.SCHEDULE_TRIGGER]: EditScheduleTriggerBlock,
  [WorkflowStateType.API_ENDPOINT]: EditAPIEndpointBlock,
  [WorkflowStateType.API_GATEWAY]: EditAPIEndpointBlock,
  [WorkflowStateType.API_GATEWAY_RESPONSE]: EditAPIResponseBlock,
  [WorkflowStateType.SQS_QUEUE]: EditQueueBlock
};
