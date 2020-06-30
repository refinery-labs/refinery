import json

from mock import patch

from assistants.user_creation_assistant import UserCreationAssistant
from controller.auth.oauth_user_data import GithubUserData
from models import UserOAuthAccountModel, UserOAuthDataRecordModel
from services.auth.oauth_service import OAuthService
from tests_utils.mocks.github import MockGithubDependenciesHolder, MockGithubDependencies
from tests_utils.mocks.user import MockUserCreationAssistantDependencies
from tests_utils.tornado_test_utils import create_future
from tests_utils.unit_test_base import ServerUnitTestBase

from tornado.testing import AsyncHTTPTestCase, gen_test


class TestOAuth( ServerUnitTestBase, AsyncHTTPTestCase ):

    def setUp(self):
        super(TestOAuth, self).setUp()

    @gen_test(timeout=10)
    def test_oauth_service_add_token_for_user_new_user(self):
        user = self.create_test_user()

        oauth_service = self.app_object_graph.provide(OAuthService)  # type: OAuthService

        oauth_user_data = GithubUserData( 'github', 'test@test.com', 'test', 'test_access_token', '{"user_data": "response"}' )

        oauth_service.add_token_for_user(self.dbsession, user, oauth_user_data)
        self.dbsession.commit()

        user_oauth_account = self.dbsession.query( UserOAuthAccountModel ).filter(
            UserOAuthAccountModel.user_id == user.id,
            UserOAuthAccountModel.provider == 'github'
        ).first()

        assert user_oauth_account is not None

        assert self.dbsession.query( UserOAuthDataRecordModel ).filter(
            UserOAuthDataRecordModel.oauth_account_id == user_oauth_account.id
        ).first() is not None

    @gen_test(timeout=10)
    def test_oauth_service_add_token_for_user_existing_user(self):
        user = self.create_test_user()

        oauth_user_data = GithubUserData( 'github', 'test@test.com', 'test', 'test_access_token', '{"user_data": "response"}' )

        user_oauth_account = UserOAuthAccountModel(oauth_user_data.provider, oauth_user_data.provider_unique_id, user.id)
        self.dbsession.add(user_oauth_account)
        self.dbsession.commit()

        oauth_service = self.app_object_graph.provide(OAuthService)  # type: OAuthService

        oauth_service.add_token_for_user(self.dbsession, user, oauth_user_data)
        self.dbsession.commit()

        user_oauth_account = self.dbsession.query( UserOAuthAccountModel ).filter(
            UserOAuthAccountModel.user_id == user.id,
            UserOAuthAccountModel.provider == 'github'
        ).first()

        assert user_oauth_account is not None

        assert self.dbsession.query( UserOAuthDataRecordModel ).filter(
            UserOAuthDataRecordModel.oauth_account_id == user_oauth_account.id
        ).first() is not None
