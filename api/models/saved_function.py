from initiate_database import *
import json
import uuid
import time
import os

class SavedFunction( Base ):
	__tablename__ = "saved_functions"

	id = Column(CHAR(36), primary_key=True)
	language = Column(Text())
	name = Column(Text())
	description = Column(Text())
	code = Column(Text())
	libraries = Column(Text())
	timestamp = Column(Integer())
	
	# Parent user the saved function
	user_id = Column(
		CHAR(36),
		ForeignKey(
			"users.id"
		)
	)

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [ "id", "name", "language", "description", "code", "libraries", "timestamp" ]
		json_attributes = [ "libraries" ]
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