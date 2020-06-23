import json
import uuid

from tornado.testing import AsyncHTTPTestCase, gen_test

from models import AWSAccount
from tests_utils.mocks.aws import MockAWSDependenciesHolder
from tests_utils.mocks.task_spawner import MockTaskSpawnerHolder
from tests_utils.tornado_test_utils import create_future
from tests_utils.unit_test_base import ServerUnitTestBase


class TestAssumeAccounts(ServerUnitTestBase, AsyncHTTPTestCase):
	mock_aws = None
	mock_task_spawner = None

	def setUp(self):
		super(TestAssumeAccounts, self).setUp()

		self.mock_aws = self.app_object_graph.provide(MockAWSDependenciesHolder)
		self.mock_task_spawner = self.app_object_graph.provide(MockTaskSpawnerHolder).task_spawner

	def create_test_aws_account(self, org, account_status, account_id="test_id"):
		aws_account = AWSAccount()
		aws_account.organization_id = org.id
		aws_account.aws_account_status = account_status
		aws_account.s3_bucket_suffix = ""
		aws_account.region = "us-west-2"
		aws_account.account_id = account_id
		return self.create_and_save_obj(aws_account)

	@gen_test(timeout=10)
	def test_assume_account_role(self):
		user_uuid = uuid.uuid4()
		response = yield self.http_client.fetch(
			self.get_url("/services/v1/assume_account_role/{user_uuid}".format(user_uuid=user_uuid)),
			method='GET',
			headers={
				"X-Service-Secret": "FAKE_TESTING_VALUE"
			},
			follow_redirects=False,
			raise_error=False
		)
		assert response.code == 302

	@gen_test(timeout=10)
	def test_assume_role_credentials(self):
		test_val = "FAKE_TESTING_VALUE"
		self.mock_task_spawner.get_assume_role_credentials.return_value = create_future(dict(
			access_key_id=test_val,
			secret_access_key=test_val,
			session_token=test_val,
			expiration_date=test_val,
			assumed_role_id=test_val,
			role_session_name=test_val,
			arn=test_val
		))

		user_uuid = uuid.uuid4()
		response = yield self.http_client.fetch(
			self.get_url("/services/v1/assume_role_credentials/{user_uuid}".format(user_uuid=user_uuid)),
			method='GET',
			headers={
				"X-Service-Secret": "FAKE_TESTING_VALUE"
			}
		)
		json_resp = json.loads(response.body)
		assert json_resp['success'] is True

	@gen_test(timeout=10)
	def test_maintain_aws_account_pool(self):
		test_val = "FAKE_TESTING_VALUE"
		self.mock_task_spawner.terraform_configure_aws_account.return_value = create_future(dict(
			redis_hostname=test_val,
			terraform_state=test_val,
			ssh_public_key=test_val,
			ssh_private_key=test_val
		))
		self.mock_task_spawner.freeze_aws_account.return_value = dict()
		self.mock_task_spawner.create_new_sub_aws_account.return_value = create_future(dict())

		user1 = self.create_test_user(email="user1@test.com")
		user2 = self.create_test_user(email="user2@test.com")
		org1 = self.create_test_user_organization(user1.id)
		org2 = self.create_test_user_organization(user2.id)

		aws_account_available = self.create_test_aws_account(org1, "AVAILABLE", account_id="account1")
		aws_account_created = self.create_test_aws_account(org2, "CREATED", account_id="account2")

		response = yield self.http_client.fetch(
			self.get_url("/services/v1/maintain_aws_account_pool"),
			method='GET',
			headers={
				"X-Service-Secret": "FAKE_TESTING_VALUE"
			}
		)
		assert response.code != 500
