from tornado import gen
from controller.base import BaseHandler

from utils.general import logit

# noinspection PyMethodOverriding, PyAttributeOutsideInit
class ClearStripeInvoiceDrafts( BaseHandler ):

	def _initialize(self, billing_spawner):
		"""
		:type dependencies: Object
		"""
		self.billing_spawner = billing_spawner

	@gen.coroutine
	def get( self ):
		logit( "Clearing all draft Stripe invoices..." )
		yield self.billing_spawner.clear_draft_invoices()

		self.write({
			"success": True,
			"msg": "Invoice drafts have been cleared!"
		})