import { SupportedLanguage, WorkflowRelationshipType, WorkflowStateType } from '@/types/graph';
import { ActiveSidebarPaneToContainerMapping, SIDEBAR_PANE } from '@/types/project-editor-types';
import AddBlockPane from '@/components/ProjectEditor/AddBlockPane';
import AddTransitionPane from '@/components/ProjectEditor/AddTransitionPane';
import EditBlockPane from '@/components/ProjectEditor/EditBlockPane';
import {HTTP_METHOD} from "@/constants/api-constants";
import DeployProjectPane from '@/components/ProjectEditor/DeployProjectPane';
import ExportProjectPane from '@/components/ProjectEditor/ExportProjectPane';
import ViewApiEndpointsPane from '@/components/DeploymentViewer/ViewApiEndpointsPane';
import ViewExecutionsPane from '@/components/DeploymentViewer/ViewExecutionsPane';
import ViewDeployedBlockPane from '@/components/DeploymentViewer/ViewDeployedBlockPane';
import ViewDeployedTransitionPane from '@/components/DeploymentViewer/ViewDeployedTransitionPane';
import DestroyDeploymentPane from '@/components/DeploymentViewer/DestroyDeploymentPane';
import {VueConstructor} from 'vue';
import {EditLambdaBlock} from '@/components/ProjectEditor/block-components/EditLambdaBlockPane';
import {EditAPIEndpointBlock} from '@/components/ProjectEditor/block-components/EditAPIEndpointBlockPane';
import {EditQueueBlock} from '@/components/ProjectEditor/block-components/EditQueuePane';
import {EditAPIResponseBlock} from '@/components/ProjectEditor/block-components/EditAPIResponseBlockPane';
import {EditScheduleTriggerBlock} from '@/components/ProjectEditor/block-components/EditScheduleTriggerBlockPane';
import {EditTopicBlock} from '@/components/ProjectEditor/block-components/EditTopicBlockPane';
import RunEditorCodeBlockPane from '@/components/ProjectEditor/RunEditorCodeBlockPane';

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

export type BlockTypeToImage = { [key in WorkflowStateType]: AddGraphElementConfig };

export interface BlockTypeConfig extends BlockTypeToImage {
  [index: string]: AddGraphElementConfig;
  saved_lambda: AddGraphElementConfig;
}

// A little bit of impedance mismatch going on, unfortunately.
export const blockTypeToImageLookup: BlockTypeConfig = {
  [WorkflowStateType.API_ENDPOINT]: {
    path: require('../../public/img/node-icons/api-gateway.png'),
    name: 'API Endpoint Block',
    description:
      'Creates a web endpoint and passes web request data to the connected Lambda Block. ' +
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
      'Returns the output from a Lambda Block to the web request started by the API Endpoint block. ' +
      'Must be downstream from an API Endpoint block, ' +
      'responses which take over 29 seconds will time out the API Endpoint response.'
  },
  [WorkflowStateType.LAMBDA]: {
    path: require('../../public/img/node-icons/code-icon.png'),
    name: 'Code Block',
    description:
      'Runs a user-defined script in PHP/Python/Node. ' +
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
      'Concurrently executes all Lambda Blocks connected to it and passes the input to the connected ' +
      'blocks. For example, take some input data and then immediately execute three Lambda blocks with that input.'
  },
  [WorkflowStateType.SQS_QUEUE]: {
    path: require('../../public/img/node-icons/sqs_queue.png'),
    name: 'Queue Block',
    description:
      'Takes input items to process and sends them to the connected Lambda Block. ' +
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
def main( lambda_input, context ):
    return False
`,
  [SupportedLanguage.NODEJS_8]: `
async function main( lambda_input, context ) {
	return false;
}
`,
  [SupportedLanguage.PHP7]: `
<?php
// Uncomment if you specified libraries
// require __DIR__ . "/vendor/autoload.php";
function main( $lambda_input, $context ) {
	return false;
}
`,
  [SupportedLanguage.GO1_12]: `package main

import (
	// The following imports are required
	// by the Refinery runtime do not remove them!
	"os"
	"fmt"
	"encoding/json"
	"runtime/debug"
	// Add your imports below this line
)

// Modify BlockInput to conform to your input data schema
type BlockInput struct {
	Example string \`json:"example"\`
}

// Modify block_main() appropriately.
// It must return a JSON-serializable value
func block_main(block_input []byte, context map[string]interface{}) bool {
	var unmarshalled_input BlockInput
	
	// lambda_input is a byte array of the input to this code block
	// This is a JSON-serialized value returned from another block.
	json.Unmarshal(block_input, &unmarshalled_input)
	
	return false
}
`
};

export const CODE_BLOCK_DEFAULT_STATE = {
  language: 'python2.7',
  code: DEFAULT_LANGUAGE_CODE[SupportedLanguage.PYTHON_2],
  memory: 768,
  libraries: [],
  layers: [],
  max_execution_time: 120,
  type: WorkflowStateType.LAMBDA
};

export const SCHEDULE_EXPRESSION_BLOCK_DEFAULT_STATE = {
  description: 'Deployed by Refinery',
  input_string: '',
  schedule_expression: 'rate(2 minutes)',
  type: WorkflowStateType.SCHEDULE_TRIGGER
};

export const TOPIC_BLOCK_DEFAULT_STATE = {
  type: WorkflowStateType.SNS_TOPIC
};

export const QUEUE_BLOCK_DEFAULT_STATE = {
  batch_size: 1,
  type: WorkflowStateType.SQS_QUEUE
};

export const API_ENDPOINT_BLOCK_DEFAULT_STATE = {
  api_path: "/",
  http_method: HTTP_METHOD.GET,
  type: WorkflowStateType.API_ENDPOINT
};

export const API_GATEWAY_RESPONSE_BLOCK_DEFAULT_STATE = {
  type: WorkflowStateType.API_GATEWAY_RESPONSE
};

export type BlockTypeToDefaultState = { [key in WorkflowStateType]: Object };

export const blockTypeToDefaultStateMapping: BlockTypeToDefaultState = {
  [WorkflowStateType.LAMBDA]: CODE_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.SQS_QUEUE]: QUEUE_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.API_GATEWAY_RESPONSE]: API_GATEWAY_RESPONSE_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.API_ENDPOINT]: API_ENDPOINT_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.SCHEDULE_TRIGGER]: SCHEDULE_EXPRESSION_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.SNS_TOPIC]: TOPIC_BLOCK_DEFAULT_STATE,
  [WorkflowStateType.API_GATEWAY]: {}
};

export const paneToContainerMapping: ActiveSidebarPaneToContainerMapping = {
  [SIDEBAR_PANE.runEditorCodeBlock]: RunEditorCodeBlockPane,
  [SIDEBAR_PANE.runDeployedCodeBlock]: RunEditorCodeBlockPane,
  [SIDEBAR_PANE.addBlock]: AddBlockPane,
  [SIDEBAR_PANE.addTransition]: AddTransitionPane,
  [SIDEBAR_PANE.allBlocks]: AddBlockPane,
  [SIDEBAR_PANE.allVersions]: AddBlockPane,
  [SIDEBAR_PANE.exportProject]: ExportProjectPane,
  [SIDEBAR_PANE.deployProject]: DeployProjectPane,
  [SIDEBAR_PANE.saveProject]: AddBlockPane,
  [SIDEBAR_PANE.editBlock]: EditBlockPane,
  [SIDEBAR_PANE.editTransition]: AddBlockPane,
  [SIDEBAR_PANE.viewApiEndpoints]: ViewApiEndpointsPane,
  [SIDEBAR_PANE.viewExecutions]: ViewExecutionsPane,
  [SIDEBAR_PANE.destroyDeploy]: DestroyDeploymentPane,
  [SIDEBAR_PANE.viewDeployedBlock]: ViewDeployedBlockPane,
  [SIDEBAR_PANE.viewDeployedTransition]: ViewDeployedTransitionPane
};

export const blockNameText = 'Name of the block.';
export const returnDataText = 'Data returned from the Lambda.';
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
