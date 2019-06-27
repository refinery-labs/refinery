from initiate_database import *
import json
import uuid
import time
import os

class SavedBlock( Base ):
	__tablename__ = "saved_blocks"

	id = Column(CHAR(36), primary_key=True)
	name = Column(Text())
	type = Column(Text())
	description = Column(Text())
	
	# Share status of the block
	# Valid values are PRIVATE, PUBLISHED
	# A block version cannot go from PUBLISHED to PRIVATE
	share_status = Column(Text())
	
	timestamp = Column(Integer())
	
	# Parent user the saved function
	user_id = Column(
		CHAR(36),
		ForeignKey(
			"users.id"
		)
	)

	# Versions of the saved block
	versions = relationship(
		"SavedBlockVersion",
		backref="saved_blocks",
		lazy="dynamic",
		cascade="all, delete-orphan"
	)

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.share_status = "PRIVATE"
		self.timestamp = int( time.time() )

	def __str__( self ):
		return self.id