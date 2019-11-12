from initiate_database import *
import json
import uuid
import time
import os

class CachedBlockIO( Base ):
	"""
	This table stores input and output data for Code Blocks. This is used
	to help construct transforms more easily for Code Blocks.
	"""
	__tablename__ = "cached_block_io"

	id = Column(Text(), primary_key=True)

	# The ID of the Code Block
	block_id = Column(
		Text(),
		nullable=False
	)

	# Origin of the return data, can be:
	# * DEPLOYMENT
	# * EDITOR
	origin = Column(
		Text(),
		nullable=False
	)

	# IO type, whether it's the INPUT or RETURN
	# to the given block.
	io_type = Column(
		Text(),
		nullable=False
	)

	# The ID of the log data, so we don't store the same
	# production log input twice
	log_id = Column(
		Text(),
		nullable=False,
		unique=True
	)

	# The raw data for the given Code Block
	body = Column(Text())
	
	timestamp = Column(Integer())
	
	# Parent user the saved function
	user_id = Column(
		CHAR(36),
		ForeignKey(
			"users.id"
		),
		nullable=False
	)

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"block_id",
			"origin",
			"io_type",
			"body",
			"timestamp"
		]
		
		return_dict = {}

		for attribute in exposed_attributes:
			return_dict[ attribute ] = getattr( self, attribute )

		return return_dict

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )

	def __str__( self ):
		return self.id