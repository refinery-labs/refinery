import time
import json
import tornado
import tornado.websocket
import datetime
import functools

from utils.general import logit

"""
This is a dict which automatically routes messages from running
Lambdas to the subscribing websocket connections.

{
	"debug_id": {
		"lambdas": [ {{WS_CONN_OBJECT}} ], # The Lambda(s) publishing to this debug ID
		"users": [ {{WS_CONNECT_OBJECT}} ] # The web browsers listening for this debug_id
	}
}
"""


class WebsocketRouter:
    def __init__(self):
        self.WEBSOCKET_ROUTER = {}

    def initialize_debug_id(self, debug_id):
        """
        Set up the default (empty) data structure for the
        WEBSOCKET_ROUTER auto-expiring dict.
        """
        self.WEBSOCKET_ROUTER[debug_id] = {
            "lambdas": [],
            "users": []
        }

    def add_subscriber(self, debug_id, websocket_connection):
        if not self.has_debug_id(debug_id):
            self.initialize_debug_id(debug_id)

        if not websocket_connection in self.WEBSOCKET_ROUTER[debug_id]["users"]:
            logit("Adding user subscription to WebSocket router...")
            self.WEBSOCKET_ROUTER[debug_id]["users"].append(
                websocket_connection
            )

    def add_lambda(self, debug_id, websocket_connection):
        if not self.has_debug_id(debug_id):
            self.initialize_debug_id(debug_id)

        if not websocket_connection in self.WEBSOCKET_ROUTER[debug_id]["lambdas"]:
            logit("Adding Lambda to WebSocket router...")
            self.WEBSOCKET_ROUTER[debug_id]["lambdas"].append(
                websocket_connection
            )

    def has_debug_id(self, debug_id):
        return (debug_id in self.WEBSOCKET_ROUTER)

    def broadcast_message_to_subscribers(self, debug_id, message_dict):
        websocket_connections = self.WEBSOCKET_ROUTER[debug_id]["users"]
        for websocket_connection in websocket_connections:
            websocket_connection.write_message(
                json.dumps(
                    message_dict
                )
            )

    def clear_if_empty(self, debug_id):
        """
        Clear the WebSocket router if there are no more active connections.
        """
        lambdas_empty = len(self.WEBSOCKET_ROUTER[debug_id]["lambdas"]) == 0
        users_empty = len(self.WEBSOCKET_ROUTER[debug_id]["users"]) == 0

        if lambdas_empty and users_empty:
            del self.WEBSOCKET_ROUTER[debug_id]

    def clean_connection_from_websocket_router(self, websocket_connection):
        logit("Garbage collecting the WebSocket router...")

        debug_ids = list(self.WEBSOCKET_ROUTER.keys())

        for debug_id in debug_ids:
            try:
                self.WEBSOCKET_ROUTER[debug_id]["lambdas"].remove(
                    websocket_connection
                )
                self.clear_if_empty(debug_id)
                logit("Cleared existing Lambda websocket connection from WebSocket Router! (Debug ID: " + debug_id + ")")
            except ValueError:
                pass

            try:
                self.WEBSOCKET_ROUTER[debug_id]["users"].remove(
                    websocket_connection
                )
                self.clear_if_empty(debug_id)
                logit("Cleared existing Refinery user websocket connection from WebSocket Router! (Debug ID: " + debug_id + ")")
            except ValueError:
                pass

    def send_heartbeed(self):
        websockets_to_ping = []
        for debug_id, websocket_metadata in self.WEBSOCKET_ROUTER.items():
            websockets_to_ping = websockets_to_ping + websocket_metadata["users"]

        for websocket_to_ping in websockets_to_ping:
            websocket_to_ping.write_message({
                "action": "HEARTBEAT",
                "version": "1.0.0",
                "source": "SERVER",
                "timestamp": int(time.time())
            })


def run_scheduled_heartbeat(websocket_object):
    logit("Sending heartbeat to all connected Websocket users...", "debug")
    websocket_object.send_heartbeed()
    # noinspection PyUnresolvedReferences
    tornado.ioloop.IOLoop.instance().add_timeout(
        datetime.timedelta(
            seconds=5
        ),
        functools.partial(
            run_scheduled_heartbeat,
            websocket_object
        )
    )


class ScheduledHeartbeatRunner:
    def __init__(self, websocket_router):
        self.run_scheduled_hearbeat_partial = functools.partial(
            run_scheduled_heartbeat,
            websocket_router
        )

    # noinspection PyUnresolvedReferences
    def start(self):
        tornado.ioloop.IOLoop.instance().add_timeout(
            datetime.timedelta(
                seconds=5
            ),
            self.run_scheduled_hearbeat_partial
        )
