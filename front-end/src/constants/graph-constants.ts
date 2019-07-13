import { ExecutionStatusType } from '@/types/api-types';
import { STYLE_CLASSES } from '@/lib/cytoscape-styles';

export const CURRENT_BLOCK_SCHEMA = '1.0.0';
export const CURRENT_TRANSITION_SCHEMA = '1.0.0';

export const GRAPH_ICONS = {
  lambda: {
    url: '/img/code-icon.png',
    id: 'lambda'
  },
  sqs_queue: {
    url: '/img/sqs_queue.png',
    id: 'sqs_queue'
  },
  schedule_trigger: {
    url: '/img/clock-icon.png',
    id: 'schedule_trigger'
  },
  sns_topic: {
    url: '/img/sns-topic.png',
    id: 'sns_topic'
  },
  api_endpoint: {
    url: '/img/api-gateway.png',
    id: 'api_endpoint'
  },
  api_gateway_response: {
    url: '/img/api-gateway.png',
    id: 'api_gateway_response'
  }
};

export type ExecutionStatusTypeToClass = { [key in ExecutionStatusType]: STYLE_CLASSES };

export const excecutionStatusTypeToClass: ExecutionStatusTypeToClass = {
  [ExecutionStatusType.EXCEPTION]: STYLE_CLASSES.EXECUTION_FAILURE,
  [ExecutionStatusType.CAUGHT_EXCEPTION]: STYLE_CLASSES.EXECUTION_CAUGHT,
  [ExecutionStatusType.SUCCESS]: STYLE_CLASSES.EXECUTION_SUCCESS
};
