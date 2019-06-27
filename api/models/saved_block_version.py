from initiate_database import *
from saved_block import SavedBlock
import json
import uuid
import time
import os

class SavedBlockVersion( Base ):
	__tablename__ = "saved_block_versions"
	
	id = Column(CHAR(36), primary_key=True)
	saved_block_id = Column(
		CHAR(36),
		ForeignKey( SavedBlock.id ),
		primary_key=True
	)
	
	version = Column(
		Integer()
	)
	
	block_object = Column(Text())
	
	timestamp = Column(Integer())

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"project_id",
			"version",
			"block_object",
			"timestamp"
		]
		
		json_attributes = [ "block_object" ]
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