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

	@property
	def shared_files( self ):
		"""
		Returns an empty list by default.
		"""
		if self._shared_files == None:
			return []
		return self._shared_files

	@shared_files.setter
	def shared_files(self, value):
		self._shared_files = value

	_shared_files = Column(
		"shared_files",
		JSON()
	)
	shared_files = synonym(
		'_shared_files',
		descriptor=shared_files
	)

	timestamp = Column(Integer())

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )
		
	def __str__( self ):
		return self.id