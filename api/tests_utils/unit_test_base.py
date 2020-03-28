import os
import sys
from sqlalchemy import create_engine
from server import make_app
from models.initiate_database import create_scoped_db_session_maker, Base
from tests_utils.hypothesis_unit_test_base import HypothesisUnitTestBase
from config.app_config import load_app_config
import pkg_resources

def add_sqlite_json_shim():
	# Include this directory in python's path to allow `jsonsqliteplugin` to be discovered by sqlalchemy
	sys.path.append(os.path.dirname(__file__))

	distribution = pkg_resources.Distribution(__file__)
	entry_points = {
		"sqlalchemy.plugins": {
			"jsonplugin": pkg_resources.EntryPoint.parse("jsonplugin = sqlite_json:JsonPlugin", dist=distribution)
		}
	}
	distribution._ep_map = entry_points
	pkg_resources.working_set.add(distribution)


class ServerUnitTestBase( HypothesisUnitTestBase ):
	"""
	Base class to inherit from for tests that need to hit a Refinery server instance.
	The instance of the application is created
	"""
	deps = dict()

	def mocked_dependencies( self, app_config ):
		add_sqlite_json_shim()
		engine = create_engine( 'sqlite:///:memory:', encoding="utf8", plugins=["jsonplugin"] )

		Base.metadata.create_all( engine )

		db_session_maker = create_scoped_db_session_maker(engine)
		mocked_deps = dict(
			db_session_maker=db_session_maker
		)
		return mocked_deps

	def get_app( self ):
		"""
		Creates an instance of the app for the Tornado test base
		:return:
		"""

		test_app_config = load_app_config("test")

		return make_app(
			test_app_config,
			self.get_tornado_app_config(),
			mocked_deps=self.mocked_dependencies( test_app_config )
		)

	def get_tornado_app_config( self ):
		return {
			"debug": False,
			"ngrok_enabled": False,
			"cookie_secret": "oogaboogatesttest112",
			"compress_response": False,
			"websocket_router": None
		}
