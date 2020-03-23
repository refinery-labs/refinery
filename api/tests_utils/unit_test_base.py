
from server import make_app
from tests_utils.hypothesis_unit_test_base import HypothesisUnitTestBase


class ServerUnitTestBase( HypothesisUnitTestBase ):
	"""
	Base class to inherit from for tests that need to hit a Refinery server instance.
	The instance of the application is created
	"""

	def get_app( self ):
		"""
		Creates an instance of the app for the Tornado test base
		:return:
		"""

		return make_app(
			self.get_tornado_app_config()
		)

	def get_tornado_app_config( self ):
		return {
			"debug": False,
			"ngrok_enabled": False,
			"cookie_secret": "oogaboogatesttest112",
			"compress_response": False
		}
