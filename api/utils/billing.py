import os
import stripe
import tornado

from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen

from utils.base_spawner import BaseSpawner

# Initialize Stripe
stripe.api_key = os.environ.get( "stripe_api_key" )

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

	@run_on_executor
	def get_account_cards( self, stripe_customer_id ):
		return BillingSpawner._get_account_cards( stripe_customer_id )
		
	@staticmethod
	def _get_account_cards( stripe_customer_id ):
		# Pull all of the metadata for the cards the customer
		# has on file with Stripe
		cards = stripe.Customer.list_sources(
			stripe_customer_id,
			object="card",
			limit=100,
		)
		
		# Pull the user's default card and add that
		# metadata to the card
		customer_info = BillingSpawner._get_stripe_customer_information(
			stripe_customer_id
		)
		
		for card in cards:
			is_primary = False
			if card[ "id" ] == customer_info[ "default_source" ]:
				is_primary = True
			card[ "is_primary" ] = is_primary
		
		return cards[ "data" ]

	@run_on_executor
	def get_stripe_customer_information( self, stripe_customer_id ):
		return BillingSpawner._get_stripe_customer_information( stripe_customer_id )
		
	@staticmethod
	def _get_stripe_customer_information( stripe_customer_id ):
		return stripe.Customer.retrieve(
			stripe_customer_id
		)

billing_spawner = BillingSpawner()