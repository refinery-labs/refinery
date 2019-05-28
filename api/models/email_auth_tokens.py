from initiate_database import *
import binascii
import json
import uuid
import time
import os

class EmailAuthToken( Base ):
	__tablename__ = "email_auth_tokens"

	id = Column(
		CHAR(36),
		primary_key=True
	)
	
	# Cryptographically random token for authentication
	# via a unique token sent to a user's email on file
	token = Column(Text())
	
	# Boolean to set if the token is expired
	# This should be set to True if the token has been used.
	# OR if the token becomes too old
	# Currently the expire age for a token is 3 hours.
	is_expired = Column(Boolean())
	
	# Parent user the auth token belongs to
	user_id = Column(
		CHAR(36),
		ForeignKey(
			"users.id"
		)
	)

	# The "user" attribute is also mapped to this object
	# via the SQLAlchemy backref function
	
	timestamp = Column(Integer())

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.token = binascii.hexlify(
			os.urandom(32)
		)
		self.expired = False
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"token",
			"expired",
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