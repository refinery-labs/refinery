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


def get_tornado_app_config():
	return {
		"debug": False,
		"ngrok_enabled": False,
		"cookie_secret": "oogaboogatesttest112",
		"compress_response": False,
		"websocket_router": None
	}


class ServerUnitTestBase( HypothesisUnitTestBase ):
	"""
	Base class to inherit from for tests that need to hit a Refinery server instance.
	The instance of the application is created
	"""
	db_session_maker = None
	dbsession = None

	def tearDown(self):
		self.dbsession.close()

	def mocked_dependencies( self ):
		add_sqlite_json_shim()
		engine = create_engine( 'sqlite:///:memory:', encoding="utf8", plugins=["jsonplugin"] )

		Base.metadata.create_all( engine )

		db_session_maker = create_scoped_db_session_maker(engine)
		mocked_deps = dict(
			db_session_maker=db_session_maker
		)
		return mocked_deps

	def create_and_save_obj( self, obj ):
		self.dbsession.add(obj)
		self.dbsession.commit()

		if hasattr(obj, 'to_dict'):
			obj_dict = obj.to_dict()
		else:
			obj_dict = dict(obj)

		return obj_dict

	def get_app( self ):
		"""
		Creates an instance of the app for the Tornado test base
		:return:
		"""
		mocked_deps = self.mocked_dependencies()

		self.db_session_maker = mocked_deps[ 'db_session_maker' ]
		self.dbsession = self.db_session_maker()

		test_app_config = load_app_config("test")

		return make_app(
			test_app_config,
			get_tornado_app_config(),
			mocked_deps=mocked_deps
		)
