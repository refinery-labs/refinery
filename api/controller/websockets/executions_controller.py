import json

import pinject
import tornado.websocket

from controller.websockets.dependency_injection import TornadoWebsocketInjectionMixin
from utils.general import logit
from utils.websocket import parse_websocket_message


class ExecutionsControllerServerDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, app_config, websocket_router):
        pass


class ExecutionsControllerServer(TornadoWebsocketInjectionMixin, tornado.websocket.WebSocketHandler):
    dependencies = ExecutionsControllerServerDependencies
    app_config = None
    websocket_router = None

    _connected_front_end_clients = []

    def open(self):
        logit("A new Refinery has connected to us from " + self.request.remote_ip)
        self._connected_front_end_clients.append(self)

    def on_message(self, message):
        message_contents = parse_websocket_message(message)

        if not message_contents:
            logit("Received invalid WebSocket message from Refinery user!")
            logit(message)
            return

        debug_id = message_contents["debug_id"]

        if "action" in message_contents and message_contents["action"] == "SUBSCRIBE":
            logit("User subscribed to debug ID " + debug_id)
            self.websocket_router.add_subscriber(
                debug_id,
                self
            )

    def on_close(self):
        logit("Refinery user has disconnected from us, remote IP: " + self.request.remote_ip)
        self._connected_front_end_clients.remove(self)
        self.websocket_router.clean_connection_from_websocket_router(
            self
        )

    def check_origin(self, origin):
        allowed_origins = json.loads(self.app_config.get("access_control_allow_origins"))

        return origin in allowed_origins
