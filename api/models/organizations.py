from initiate_database import *
import json
import uuid
import time
import os

class Organization( Base ):
	"""
	An organization is a group of users.
	
	The organization in multiple ways, as a way
	to hold AWS accounts, users, etc.
	"""
	__tablename__ = "organizations"
	
	id = Column(
		CHAR(36),
		primary_key=True
	)
	
	# Name of the organization
	name = Column(Text())
	
	# Max users, an attribute for billing
	max_users = Column(BigInteger())
	
	# Whether the organization is disabled
	disabled = Column(Boolean())
	
	# Child users to the organization
	users = relationship(
		"User",
		lazy="dynamic",
		# When an org is deleted, all users should be deleted too
		cascade="all, delete-orphan"
	)
	
	# Child AWS accounts to the organization
	aws_accounts = relationship(
		"AWSAccount",
		lazy="dynamic",
		# When an org is deleted, all AWS accounts should be deleted too
		cascade="all, delete-orphan"
	)
	
	timestamp = Column(Integer())

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.max_users = 1
		self.disabled = False
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"name",
			"max_users",
			"disabled",
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