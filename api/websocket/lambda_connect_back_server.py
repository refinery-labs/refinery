import json
import tornado.websocket

from utils.general import attempt_json_decode, logit

def parse_websocket_message( input_message ):
	"""
	Returns the dictionary if it's a valid message and
	returns False if it is not.
	"""
	message_contents = attempt_json_decode(
		input_message
	)
	
	# Reject it if it's not a dict
	if type( message_contents ) != dict:
		return False
	
	# Reject it if it doesn't contain a "debug_id"
	if not "debug_id" in message_contents:
		return False
	
	return message_contents

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
class WebSocketRouter:
	def __init__( self ):
		self.WEBSOCKET_ROUTER = {}
		
	def initialize_debug_id( self, debug_id ):
		"""
		Set up the default (empty) data structure for the
		WEBSOCKET_ROUTER auto-expiring dict.
		"""
		self.WEBSOCKET_ROUTER[ debug_id ] = {
			"lambdas": [],
			"users": []
		}
		
	def add_subscriber( self, debug_id, websocket_connection ):
		if not self.has_debug_id( debug_id ):
			self.initialize_debug_id( debug_id )
			
		if not websocket_connection in self.WEBSOCKET_ROUTER[ debug_id ][ "users" ]:
			logit( "Adding user subscription to WebSocket router..." )
			self.WEBSOCKET_ROUTER[ debug_id ][ "users" ].append(
				websocket_connection
			)
	
	def add_lambda( self, debug_id, websocket_connection ):
		if not self.has_debug_id( debug_id ):
			self.initialize_debug_id( debug_id )
			
		if not websocket_connection in self.WEBSOCKET_ROUTER[ debug_id ][ "lambdas" ]:
			logit( "Adding Lambda to WebSocket router..." )
			self.WEBSOCKET_ROUTER[ debug_id ][ "lambdas" ].append(
				websocket_connection
			)
		
	def has_debug_id( self, debug_id ):
		return ( debug_id in self.WEBSOCKET_ROUTER )
		
	def broadcast_message_to_subscribers( self, debug_id, message_dict ):
		websocket_connections = self.WEBSOCKET_ROUTER[ debug_id ][ "users" ]
		for websocket_connection in websocket_connections:
			websocket_connection.write_message(
				json.dumps(
					message_dict
				)
			)
			
	def clear_if_empty( self, debug_id ):
		"""
		Clear the WebSocket router if there are no more active connections.
		"""
		lambdas_empty = len( self.WEBSOCKET_ROUTER[ debug_id ][ "lambdas" ] ) == 0
		users_empty = len( self.WEBSOCKET_ROUTER[ debug_id ][ "users" ] ) == 0
		
		if lambdas_empty and users_empty:
			del self.WEBSOCKET_ROUTER[ debug_id ]
			
	def clean_connection_from_websocket_router( self, websocket_connection ):
		logit( "Garbage collecting the WebSocket router..." )
		
		debug_ids = list( self.WEBSOCKET_ROUTER.keys() )
		
		for debug_id in debug_ids:
			try:
				self.WEBSOCKET_ROUTER[ debug_id ][ "lambdas" ].remove(
					websocket_connection
				)
				self.clear_if_empty( debug_id )
				logit( "Cleared existing Lambda websocket connection from WebSocket Router! (Debug ID: " + debug_id + ")" )
			except ValueError:
				pass
			
			try:
				self.WEBSOCKET_ROUTER[ debug_id ][ "users" ].remove(
					websocket_connection
				)
				self.clear_if_empty( debug_id )
				logit( "Cleared existing Refinery user websocket connection from WebSocket Router! (Debug ID: " + debug_id + ")" )
			except ValueError:
				pass
		
websocket_router = WebSocketRouter()

class LambdaConnectBackServer(tornado.websocket.WebSocketHandler):
	connected_lambdas = []
	
	def open( self ):
		logit( "A new Lambda has connected to us from " + self.request.remote_ip )
		self.connected_lambdas.append( self )
	
	def on_message( self, message ):
		message_contents = parse_websocket_message( message )
		
		if not message_contents:
			logit( "Received invalid WebSocket message from Refinery user!" )
			logit( message )
			return
		
		debug_id = message_contents[ "debug_id" ]
		
		# Add Lambda to WebSocket router, will only be added if
		# it's not already in the pool
		websocket_router.add_lambda(
			debug_id,
			self
		)
			
		websocket_router.broadcast_message_to_subscribers(
			debug_id,
			message_contents
		)
	
	def on_close(self):
		logit( "Lambda has closed the WebSocket connection, source IP: " + self.request.remote_ip )
		self.connected_lambdas.remove( self )
		websocket_router.clean_connection_from_websocket_router(
			self
		)
		
class ExecutionsControllerServer(tornado.websocket.WebSocketHandler):
	connected_front_end_clients = []
	
	def open( self ):
		logit( "A new Refinery has connected to us from " + self.request.remote_ip )
		self.connected_front_end_clients.append( self )
	
	def on_message( self, message ):
		message_contents = parse_websocket_message( message )
		
		if not message_contents:
			logit( "Received invalid WebSocket message from Refinery user!" )
			logit( message )
			return
		
		debug_id = message_contents[ "debug_id" ]
		
		if "action" in message_contents and message_contents[ "action" ] == "SUBSCRIBE":
			logit( "User subscribed to debug ID " + debug_id )
			websocket_router.add_subscriber(
				debug_id,
				self
			)
	
	def on_close( self ):
		logit( "Refinery user has disconnected from us, remote IP: " + self.request.remote_ip )
		self.connected_front_end_clients.remove( self )
		websocket_router.clean_connection_from_websocket_router(
			self
		)
		
	def check_origin(self, origin):
		# TODO do not let me go into production!
		print( "Check origin called!" )
		return True