from tornado import gen
from controller.base import BaseHandler

from utils.billing import billing_spawner
from utils.general import logit

class ClearStripeInvoiceDrafts( BaseHandler ):
	@gen.coroutine
	def get( self ):
		logit( "Clearing all draft Stripe invoices..." )
		yield billing_spawner.clear_draft_invoices()

		self.write({
			"success": True,
			"msg": "Invoice drafts have been cleared!"
		})