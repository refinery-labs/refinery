from initiate_database import *
import json
import uuid
import time
import os

class AWSAccount( Base ):
	__tablename__ = "aws_accounts"

	id = Column(
		CHAR(36),
		primary_key=True
	)
	
	# AWS account ID
	account_id = Column(Integer())
	
	# AWS access key
	access_key = Column(Text())
	
	# AWS secret key
	secret_key = Column(Text())
	
	# Parent organization the AWS account belongs to
	organization_id = Column(
		CHAR(36),
		ForeignKey(
			"organizations.id"
		)
	)
	
	# Deployments this AWS account is associated with
	deployments = relationship(
		"Deployment",
		lazy="dynamic"
	)
	
	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"account_id",
			"access_key",
			"secret_key",
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