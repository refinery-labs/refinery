import json

from models import EmailAuthToken
from tests_utils.mocks.task_spawner import MockTaskSpawnerHolder
from tests_utils.tornado_test_utils import create_future
from tests_utils.unit_test_base import ServerUnitTestBase

from tornado.testing import AsyncHTTPTestCase, gen_test


class TestAuth( ServerUnitTestBase, AsyncHTTPTestCase ):

	def setUp(self):
		super(TestAuth, self).setUp()

		self.mock_task_spawner = self.app_object_graph.provide(MockTaskSpawnerHolder).task_spawner

	def create_test_email_auth_token( self, user_id, email_verified=True ):
		email_auth_token = EmailAuthToken()
		email_auth_token.user_id = user_id
		self.dbsession.add( email_auth_token )
		self.dbsession.commit()

		user = self.get_user_from_id( user_id )
		user.email_verified = email_verified
		user.email_auth_tokens = [email_auth_token]
		self.dbsession.commit()

		return email_auth_token.to_dict()

	@gen_test(timeout=10)
	def test_send_login_email(self):
		user = self.create_test_user()

		self.mock_task_spawner.send_authentication_email.return_value = create_future()

		body = json.dumps( {'email': user.email} )
		response = yield self.http_client.fetch(
			self.get_url("/api/v1/auth/login"),
			method='POST',
			body=body,
			headers={
				"X-CSRF-Validation-Header": "True"
			}
		)
		json_resp = json.loads(response.body)
		assert json_resp['success'] is True

	@gen_test(timeout=10)
	def test_login_via_email_link(self):
		user = self.create_test_user()
		org = self.create_test_user_organization( user.id )
		email_auth_token = self.create_test_email_auth_token( user.id )

		assert org is not None

		response = yield self.http_client.fetch(
			self.get_url("/authentication/email/" + email_auth_token["token"]),
			method='GET',
			follow_redirects=False,
			raise_error=False
		)
		assert response.code == 302
