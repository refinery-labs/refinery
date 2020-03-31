import stripe

from tornado.concurrent import run_on_executor
from utils.general import logit

from utils.base_spawner import BaseSpawner


class BillingSpawner(BaseSpawner):
	@run_on_executor
	def clear_draft_invoices( self ):
		"""
		Clears all Stripe invoices which are in a "draft" state. Useful for backing out of
		a state where invalid invoices were generated and you need to clear everything out
		and then try again.
		"""
		invoice_ids_to_delete = []

		for stripe_invoice in stripe.Invoice.list():
			if stripe_invoice[ "status" ] == "draft":
				invoice_ids_to_delete.append(
					stripe_invoice[ "id" ]
				)

		for invoice_id in invoice_ids_to_delete:
			logit( "Deleting invoice ID '" + invoice_id + "'..." )
			response = stripe.Invoice.delete(
				invoice_id,
			)

		logit( "Deleting draft invoices completed successfully!" )
