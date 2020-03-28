import json
import tornado.websocket

from pyexceptions.runtime_errors import InvalidConfigurationException
from utils.general import logit
from utils.websocket import parse_websocket_message
from config.app_config import global_app_config


class ExecutionsControllerServer(tornado.websocket.WebSocketHandler):
	connected_front_end_clients = []
	websocket_router = None
	
	def initialize( self, **kwargs ):
		access_control_allow_origins = global_app_config.get( "access_control_allow_origins" )

		if access_control_allow_origins is None:
			raise InvalidConfigurationException( "Missing CORS origins" )

		self.access_control_allow_origins = access_control_allow_origins

		self.websocket_router = kwargs[ "websocket_router" ]
	
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
			self.websocket_router.add_subscriber(
				debug_id,
				self
			)
	
	def on_close( self ):
		logit( "Refinery user has disconnected from us, remote IP: " + self.request.remote_ip )
		self.connected_front_end_clients.remove( self )
		self.websocket_router.clean_connection_from_websocket_router(
			self
		)
		
	def check_origin( self, origin ):
		allowed_origins = json.loads( self.access_control_allow_origins )
		
		return ( origin in allowed_origins )