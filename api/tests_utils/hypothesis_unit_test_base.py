import unittest

from tornado.testing import AsyncTestCase


class HypothesisUnitTestBase(AsyncTestCase, unittest.TestCase):
    """
    Inheriting from this class will allow tests that leverage Tornado coroutines to run properly.
    """

    def execute_example(self, f):
        # Creates a per-test event loop and runs the provided function synchronously, which accomodates coroutines
        return self.get_new_ioloop().run_sync(f)

# Example test using this class:
#
# class TestAppConfig( HypothesisUnitTestBase ):
# 	@tornado.testing.gen_test
# 	@given(text())
# 	def test_decode_inverts_encode(self, s):
# 		self.assertEqual(s, s)
# 		raise gen.Return()
