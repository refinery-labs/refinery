from tests_utils.unit_test_base import ServerUnitTestBase

import tornado
from tornado.testing import AsyncHTTPTestCase, gen_test
from server import make_app
from config.app_config import load_app_config
from services.websocket_router import WebSocketRouter

class TestFreeTierSignup( AsyncHTTPTestCase ):
	def get_app( self ):
		"""
		Creates an instance of the app for the Tornado test base
		:return:
		"""

		return make_app(
			load_app_config("test"),
			self.get_tornado_app_config()
		)

	def get_tornado_app_config( self ):
		return {
			"debug": False,
			"ngrok_enabled": False,
			"cookie_secret": "oogaboogatesttest112",
			"compress_response": False,
			"websocket_router": WebSocketRouter()
		}
	def test_health_endpoint( self ):
		response = self.fetch( "/api/v1/health" )
		self.assertEqual( response.code, 200, "Status code is 200" )
