import {
  LambdaDebuggingWebsocketActions,
  LambdaDebuggingWebsocketMessage,
  LambdaDebuggingWebsocketSources
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
