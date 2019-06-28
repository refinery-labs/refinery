from initiate_database import *
from saved_block import SavedBlock
import json
import uuid
import time
import os

class SavedBlockVersion( Base ):
	__tablename__ = "saved_block_versions"
	
	id = Column(Text(), primary_key=True)
	saved_block_id = Column(
		Text(),
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
		
	def __str__( self ):
		return self.id