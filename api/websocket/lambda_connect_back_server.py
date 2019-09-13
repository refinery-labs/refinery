import tornado.websocket

from utils.general import attempt_json_decode, logit

"""
This is a ExpiringDict which automatically routes messages from running
Lambdas to the subscribing websocket connections.

{
	"debug_id": {
		"lambdas": [ {{WS_CONN_OBJECT}} ], # The Lambda(s) publishing to this debug ID
		"users": [ {{WS_CONNECT_OBJECT}} ] # The web browsers listening for this debug_id
	}
}
"""
WEBSOCKET_ROUTER = {}
		
def initialize_debug_id( debug_id ):
	"""
	Set up the default (empty) data structure for the
	WEBSOCKET_ROUTER auto-expiring dict.
	"""
	global WEBSOCKET_ROUTER
	
	WEBSOCKET_ROUTER[ debug_id ] = {
		"lambdas": [],
		"users": []
	}

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
	
def broadcast_message_to_subscribers( message_dict, websocket_connections ):
	for websocket_connection in websocket_connections:
		websocket_connection.write(
			json.dumps(
				message_dict
			)
		)
		
def clean_connection_from_websocket_router( websocket_connection ):
	global WEBSOCKET_ROUTER
	
	logit( "Garbage collecting the WebSocket router..." )
	
	debug_ids = list( WEBSOCKET_ROUTER.keys() )
	
	for debug_id in debug_ids:
		try:
			WEBSOCKET_ROUTER[ debug_id ][ "lambdas" ].remove(
				websocket_connection
			)
			logit( "Cleared existing Lambda websocket connection from WebSocket Router! (Debug ID: " + debug_id + ")" )
		except ValueError:
			pass
		
		try:
			WEBSOCKET_ROUTER[ debug_id ][ "users" ].remove(
				websocket_connection
			)
			logit( "Cleared existing Refinery user websocket connection from WebSocket Router! (Debug ID: " + debug_id + ")" )
		except ValueError:
			pass

class LambdaConnectBackServer(tornado.websocket.WebSocketHandler):
	connected_lambdas = []
	
	def open( self ):
		logit( "A new Lambda has connected to us from " + self.request.remote_ip )
		self.connected_lambdas.append( self )
	
	def on_message( self, message ):
		global WEBSOCKET_ROUTER
		
		message_contents = parse_websocket_message( message )
		
		if not message_contents:
			logit( "Received invalid WebSocket message from Refinery user!" )
			logit( message )
			return
		
		debug_id = message_contents[ "debug_id" ]
		
		# If there's no debug ID we need to set up an
		# empty entry in the auto-expiring WEBSOCKET_ROUTER.
		if not debug_id in WEBSOCKET_ROUTER:
			initialize_debug_id( debug_id )
			
			WEBSOCKET_ROUTER[ debug_id ][ "lambdas" ].append(
				self
			)
			return
		
		logit( "Message received from Lambda: " )
		logit( message_contents )
	
	def on_close(self):
		logit( "Lambda has closed the WebSocket connection, source IP: " + self.request.remote_ip )
		self.connected_lambdas.remove( self )
		clean_connection_from_websocket_router(
			self
		)
		
class ExecutionsControllerServer(tornado.websocket.WebSocketHandler):
	connected_front_end_clients = []
	
	def open( self ):
		logit( "A new Refinery has connected to us from " + self.request.remote_ip )
		self.connected_front_end_clients.append( self )
	
	def on_message( self, message ):
		global WEBSOCKET_ROUTER
		
		message_contents = parse_websocket_message( message )
		
		if not message_contents:
			logit( "Received invalid WebSocket message from Refinery user!" )
			logit( message )
			return
		
		debug_id = message_contents[ "debug_id" ]
		
		if not debug_id in WEBSOCKET_ROUTER:
			initialize_debug_id( debug_id )
			
			WEBSOCKET_ROUTER[ debug_id ][ "lambdas" ].append(
				self
			)
			return
		
		broadcast_message_to_subscribers(
			message_contents,
			WEBSOCKET_ROUTER[ debug_id ][ "users" ]
		)
		
		logit( "Message received from Refinery user: " )
		logit( message_contents )
	
	def on_close( self ):
		logit( "Refinery user has disconnected from us, remote IP: " + self.request.remote_ip )
		self.connected_front_end_clients.remove( self )
		clean_connection_from_websocket_router(
			self
		)