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


class TestAuth( ServerUnitTestBase, AsyncHTTPTestCase ):

    binding_specs = [
        MockGithubDependencies()
    ]

    def setUp(self):
        super(TestAuth, self).setUp()

        self.mock_github = self.app_object_graph.provide(MockGithubDependenciesHolder)

    @patch('controller.base.BaseHandler.get_secure_session_data')
    @patch('controller.base.BaseHandler.get_secure_cookie_data')
    @patch('controller.base.BaseHandler.authenticate_user_id')
    @gen_test(timeout=10)
    def test_associate_oauth_data_with_existing_user(self, authenticate_user_id, get_secure_cookie_data, get_secure_session_data):
        user = self.create_test_user()

        test_oauth_state_cookie = 'test_oauth_state_cookie'

        authenticate_user_id.return_value = None
        get_secure_session_data.return_value = dict(
            user_id=user.id
        )
        get_secure_cookie_data.return_value = test_oauth_state_cookie
        self.mock_github.github_oauth_provider.retrieve_user_via_oauth_code.return_value = create_future(GithubUserData( '1', 'test@test.com', 'test', 'test_access_token', '{"user_data": "response"}' ))

        response = yield self.http_client.fetch(
            self.get_url("/api/v1/auth/github") + '?code={code}&state={state}'.format(code='asdf', state=test_oauth_state_cookie),
            method='GET',
            raise_error=False
        )

        assert self.mock_github.user_creation_assistant.update_user_oauth_record.called
        assert authenticate_user_id.called
