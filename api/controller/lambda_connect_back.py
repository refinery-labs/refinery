import tornado

from utils.general import logit
from utils.websocket import parse_websocket_message

class LambdaConnectBackServer(tornado.websocket.WebSocketHandler):
	connected_lambdas = []
	
	def initialize( self, **kwargs ):
		self.websocket_router = kwargs[ "websocket_router" ]
	
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
		self.websocket_router.add_lambda(
			debug_id,
			self
		)
			
		self.websocket_router.broadcast_message_to_subscribers(
			debug_id,
			message_contents
		)
	
	def on_close( self ):
		logit( "Lambda has closed the WebSocket connection, source IP: " + self.request.remote_ip )
		self.connected_lambdas.remove( self )
		self.websocket_router.clean_connection_from_websocket_router(
			self
		)