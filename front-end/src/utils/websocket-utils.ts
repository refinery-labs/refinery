import {
  LambdaDebuggingWebsocketActions,
  LambdaDebuggingWebsocketMessage,
  LambdaDebuggingWebsocketSources,
  RunLambdaResult
} from '@/types/api-types';

// Parses a Lambda live debugging websocket message into the relevant interface
export function parseLambdaWebsocketMessage(websocketMessage: string) {
  const parsedMessage = JSON.parse(websocketMessage);

  const webSocketParsedMessage: LambdaDebuggingWebsocketMessage = {
    body: parsedMessage.body,
    timestamp: parsedMessage.timestamp,
    source: parsedMessage.source,
    version: parsedMessage.version,
    action: parsedMessage.action,
    debug_id: parsedMessage.debug_id
  };

  return webSocketParsedMessage;
}

export function getLambdaResultFromWebsocketMessage(
  websocketMessage: LambdaDebuggingWebsocketMessage,
  runLambdaResult: RunLambdaResult | null
) {
  // Setup our initial devLambdaResult when we get our first
  // line of output from the Lambda
  if (runLambdaResult === null) {
    return {
      is_error: false,
      version: websocketMessage.version,
      logs: websocketMessage.body,
      truncated: true,
      status_code: 200,
      arn: '',
      returned_data: ''
    };
  }

  return {
    ...runLambdaResult,
    logs: runLambdaResult.logs + websocketMessage.body
  };
}
