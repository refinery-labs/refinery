from initiate_database import *
import json
import uuid
import time
import os

class Layer( Base ):
	__tablename__ = "layers"

	id = Column(Text(), primary_key=True)
	
	# The type of the layer, generally this will just be PACKAGES
	# but for future usage this could be set to something else
	type = Column(Text())
	
	# The unique key identifying this layer, this is generally the following:
	# SHA256( language + "-" + json.dumps( libraries_object, sort_keys=True ) )
	# Basically uniquely hashed by language name + sorted JSON array of package names
	unique_hash_key = Column(Text(), unique=True)
	
	# The ARN of the Lambda Layer, used for deleting it/referencing it
	arn = Column(Text())
	
	# The version of the layer
	version = Column(Integer())
	
	# The total size of the layer.
	# Important for computing if we're close to the
	# 75GB storage limit in AWS
	size = Column(Integer())
	
	timestamp = Column(Integer())
	
	# AWS Account this layer was deployed to.
	aws_account_id = Column(
		CHAR(36),
		ForeignKey(
			"aws_accounts.id"
		)
	)

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )

	def __str__( self ):
		return self.id
		
	def to_dict( self ):
		exposed_attributes = [
			"id",
			"type",
			"unique_hash_key",
			"arn",
			"version",
			"size",
			"timestamp"
		]
		
		return_dict = {}

		for attribute in exposed_attributes:
			return_dict[ attribute ] = getattr( self, attribute )
			
		return return_dict