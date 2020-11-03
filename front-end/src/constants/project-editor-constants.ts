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
import { HTTP_METHOD } from '@/constants/api-constants';
import generateStupidName from '@/lib/silly-names';

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
  },
  [WorkflowRelationshipType.MERGE]: {
    name: 'Merge Transition',
    description:
      'Merges together two pipelines together and passes the return values of each pipeline into the input ' +
      'of the next Code Block as an array. '
  }
};

export const availableTransitions = [
  WorkflowRelationshipType.IF,
  WorkflowRelationshipType.THEN,
  WorkflowRelationshipType.ELSE,
  WorkflowRelationshipType.EXCEPTION,
  WorkflowRelationshipType.FAN_IN,
  WorkflowRelationshipType.FAN_OUT,
  WorkflowRelationshipType.MERGE
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
    fromType: WorkflowStateType.LAMBDA,
    toType: WorkflowStateType.SQS_QUEUE
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
  },
  {
    fromType: WorkflowStateType.SQS_QUEUE,
    toType: WorkflowStateType.LAMBDA
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
  },

  warmup_concurrency_level: 0
};

export type DefaultCodeFromLanguage = { [key in SupportedLanguage]: string };

export const DEFAULT_LANGUAGE_CODE: DefaultCodeFromLanguage = {
  [SupportedLanguage.RUBY2_6_4]: `
def main(block_input, backpack)
    return "Hello World!"
end
`,
  [SupportedLanguage.PYTHON_36]: `
def main(block_input, backpack):
    return "Hello World!"
`,
  [SupportedLanguage.PYTHON_38]: `
def main(block_input, backpack):
    return "Hello World!"
`,
  [SupportedLanguage.PYTHON_2]: `
def main(block_input, backpack):
    return "Hello World!"
`,
  [SupportedLanguage.NODEJS_10]: `
async function main(blockInput, backpack) {
    return 'Hello World!';
}

module.exports = { main };
`,
  [SupportedLanguage.NODEJS_1020]: `
async function main(blockInput, backpack) {
    return 'Hello World!';
}

module.exports = { main };
`,
  [SupportedLanguage.NODEJS_8]: `
async function main(blockInput, backpack) {
    return 'Hello World!';
}

module.exports = { main };
`,
  [SupportedLanguage.PHP7]: `
<?php
// Uncomment if you specified libraries
// require $_ENV["LAMBDA_TASK_ROOT"] . "/vendor/autoload.php";
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
    "io/ioutil"
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
  language: SupportedLanguage.NODEJS_8,
  code: DEFAULT_LANGUAGE_CODE[SupportedLanguage.NODEJS_8],
  memory: 768,
  libraries: [],
  layers: [],
  // Changing this to max allowed time by default because
  // that's likely what people would prefer
  max_execution_time: 900,
  type: WorkflowStateType.LAMBDA,
  environment_variables: {},
  reserved_concurrency_count: false
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
  [WorkflowStateType.API_GATEWAY]: () => SHARED_BLOCK_DEFAULTS,
  [WorkflowStateType.WARMER_TRIGGER]: () => SHARED_BLOCK_DEFAULTS
};

export const blockNameText = 'Name of the block.';
export const returnDataText = 'Data returned from the Code.';
export const languagesText = 'Language of code block.';
export const importLibsText = 'Dependencies for the code.';
export const codeEditorText = 'Code to be executed by the block.';
export const maxExecutionTimeText = 'Maximum time the code may execute before being killed in seconds.';
export const maxExecutionMemoryText = 'Maximum memory for the code to use during execution.';

export const arnRegex = /^arn:aws:lambda:us-west-2:\d+:layer:[a-zA-Z0-9-_]+:\d+$/;
export const branchNameBlacklistRegex = /[./]|\.\.|@{|[/.]$|^@$|[~^:\00-\x20\x7F\s?*[\\]/;

export const masterBranchName = 'master';

export const loadMoreProjectVersionsOptionValue = -1;
