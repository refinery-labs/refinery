import json

from tests_utils.unit_test_base import ServerUnitTestBase

from tornado.testing import AsyncHTTPTestCase, gen_test

class TestFreeTierSignup( ServerUnitTestBase, AsyncHTTPTestCase ):
	@gen_test(timeout=10)
	def test_health(self):
		response = yield self.http_client.fetch(self.get_url("/api/v1/health"))
		json_resp = json.loads(response.body)
		assert json_resp['status'] == 'ok'
