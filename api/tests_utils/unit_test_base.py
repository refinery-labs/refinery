import json
import os
import sys

import pinject
from sqlalchemy import create_engine
from sqlalchemy.testing import mock

from app import TornadoApp
from config.provider import load_app_config
from models import User, Organization
from models.initiate_database import create_scoped_db_session_maker, Base
from tests_utils.hypothesis_unit_test_base import HypothesisUnitTestBase
import pkg_resources

from tests_utils.mocks.aws import MockAWSDependencies
from tests_utils.mocks.task_spawner import MockTaskSpawner
from utils.general import UtilsBindingSpec


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


class MockDatabaseBindingSpec(pinject.BindingSpec):
    def configure(self, bind):
        pass

    @pinject.provides("db_engine")
    def provide_db_engine(self):
        add_sqlite_json_shim()
        engine = create_engine("sqlite:///:memory:", encoding="utf8", plugins=["jsonplugin"])

        Base.metadata.create_all(engine)
        return engine

    @pinject.provides("db_session_maker")
    def provide_db_session_maker(self, db_engine):
        return create_scoped_db_session_maker(db_engine)


class TestConfigBindingSpec(pinject.BindingSpec):
    def configure(self, bind):
        pass

    @pinject.provides("app_config")
    def provide_app_config(self):
        return load_app_config("test")

    @pinject.provides("tornado_config")
    def provide_tornado_config(self):
        return get_tornado_app_config()

    @pinject.provides("lambda_callback_endpoint")
    def provide_lambda_callback_endpoint(self):
        return "ws://localhost:3333/ws/v1/lambdas/connectback"


class ServerUnitTestBase(HypothesisUnitTestBase):
    """
    Base class to inherit from for tests that need to hit a Refinery server instance.
    The instance of the application is created
    """
    db_session_maker = None
    dbsession = None
    classes = []
    binding_specs = []

    app_object_graph = None

    def setUp(self):
        self._patched_task_spawner = mock.patch('assistants.task_spawner.task_spawner_assistant.TaskSpawner', autospec=True)
        super(ServerUnitTestBase, self).setUp()

    def tearDown(self):
        self._patched_task_spawner.stop()
        self.dbsession.close()

    @staticmethod
    def load_fixture(fixture_name, load_json=False):
        fixture_path = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", fixture_name)
        with open(fixture_path, 'r') as f:
            if load_json:
                return json.load(f)
            else:
                return f.read()

    def create_and_save_obj(self, obj, to_dict=False):
        self.dbsession.add(obj)
        self.dbsession.commit()

        if to_dict:
            if hasattr(obj, 'to_dict'):
                obj = obj.to_dict()
            else:
                obj = dict(obj)

        return obj

    def get_user_from_id(self, user_id):
        return self.dbsession.query(User).filter(User.id == user_id).first()

    def create_test_user_organization(self, user_id):
        org = Organization()
        self.dbsession.add(org)
        self.dbsession.commit()

        user = self.get_user_from_id(user_id)
        user.organization_id = org.id
        self.dbsession.commit()

        return org

    def create_test_user(self):
        user = User()
        user.email = "test@test.com"
        return self.create_and_save_obj(user)

    def get_app(self):
        """
        Creates an instance of the app for the Tornado test base
        :return:
        """

        common_specs = [
            MockAWSDependencies(),
            MockDatabaseBindingSpec(),
            MockTaskSpawner(self._patched_task_spawner),
            TestConfigBindingSpec(),
            UtilsBindingSpec()
        ]
        self.binding_specs = self.binding_specs + common_specs

        self.app_object_graph = pinject.new_object_graph(modules=[], classes=self.classes, binding_specs=self.binding_specs)

        """
		A hack to extract deps from object graph
		"""
        class GetDepsFromObjectGraph:
            db_session_maker = None

            @pinject.copy_args_to_public_fields
            def __init__(self, db_session_maker):
                pass

        deps_from_object_graph = self.app_object_graph.provide(GetDepsFromObjectGraph)
        self.db_session_maker = deps_from_object_graph.db_session_maker

        self.dbsession = self.db_session_maker()

        tornado_app = self.app_object_graph.provide(TornadoApp)
        return tornado_app.make_app(self.app_object_graph)
