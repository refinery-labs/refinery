import os
import stripe
import tornado

from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen

from utils.base_spawner import BaseSpawner
from config.app_config import global_app_config

# Initialize Stripe
stripe.api_key = global_app_config.get( "stripe_api_key" )

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
