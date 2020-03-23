from tests_utils.unit_test_base import ServerUnitTestBase


class TestFreeTierSignup( ServerUnitTestBase ):

	def test_health_endpoint( self ):
		response = self.fetch( "/api/v1/health" )
		self.assertEqual( response.code, 200, "Status code is 200" )
