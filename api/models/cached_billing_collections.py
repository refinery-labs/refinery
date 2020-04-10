from initiate_database import *
import json
import uuid
import time

class CachedBillingCollection( Base ):
	"""
	This is a database entry for a collection of billing line items pulled from AWS.
	Since pulling billing data from CostExplorer is fairly expensive at 1 cent per
	query we just do regular pulls and store the data in the database. Then when the
	user views their billing data we just show them the latest billing total pulled
	from AWS.
	
	We can adjust how often these totals are pulled to meet our cost needs. Likely
	this will be just daily in the beggining.
	"""
	__tablename__ = "cached_billing_collections"
	
	id = Column(
		CHAR(36),
		primary_key=True
	)
	
	# Billing start date
	billing_start_date = Column(Text())
	
	# Billing end date
	billing_end_date = Column(Text())
	
	# Billing granularity
	# "daily" || "hourly" || "monthly"
	billing_granularity = Column(Text())
	
	# Parent billing collection this item belongs to
	aws_account_id = Column(
		CHAR(36),
		ForeignKey(
			"aws_accounts.id"
		)
	)
	aws_account = relationship(
		"AWSAccount",
		back_populates="cached_billing_collections"
	)
	
	# The list of billing items in this collection
	billing_items = relationship(
		"CachedBillingItem",
		back_populates="billing_collection",
		lazy="dynamic"
	)
	
	timestamp = Column(Integer())

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"timestamp"
		]
		
		json_attributes = []
		return_dict = {}

		for attribute in exposed_attributes:
			if attribute in json_attributes:
				return_dict[ attribute ] = json.loads(
					getattr( self, attribute )
				)
			else:
				return_dict[ attribute ] = getattr( self, attribute )

		return return_dict

	def __str__( self ):
		return self.id