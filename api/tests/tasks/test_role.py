from tornado.testing import AsyncHTTPTestCase

from tests_utils.mocks.aws import MockAWSDependenciesHolder
from tests_utils.tornado_test_utils import create_future
from tests_utils.unit_test_base import ServerUnitTestBase


class TestAssumeAccounts(ServerUnitTestBase, AsyncHTTPTestCase):
	mock_aws = None

	def setUp(self):
		super(TestAssumeAccounts, self).setUp()

		self.mock_aws = self.app_object_graph.provide(MockAWSDependenciesHolder)

	def test_get_assume_role_credentials( self ):
		self.mock_aws.sts_client.assume_role.return_value = create_future({
			"Credentials": {
				"AccessKeyId": "FAKE_TESTING_VALUE",
				"SecretAccessKey": "FAKE_TESTING_VALUE",
				"SessionToken": "FAKE_TESTING_VALUE",
				"Expiration": "FAKE_TESTING_VALUE",
			},
			"AssumedRoleUser": {
				"AssumedRoleId": "FAKE_TESTING_VALUE",
				"Arn": "FAKE_TESTING_VALUE"
			}
		})

