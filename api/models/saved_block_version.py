from initiate_database import *
from saved_block import SavedBlock
import json
import uuid
import time
import os
import hashlib

from sqlalchemy.dialects.postgresql import JSONB

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

	# sha256 hash to uniquely identify this block with its hashable properties
	block_hash = Column(LargeBinary)

	# deprecated: use block_object_json
	block_object = Column(Text())

	_block_object_json = Column(
		"block_object_json",
		JSONB(astext_type=Text)
	)

	@property
	def block_object_json(self):
		return self._block_object_json

	@block_object_json.setter
	def block_object_json( self, block_json ):
		self._block_object_json = block_json

		# Update this saved block verion's hash
		self.saved_block_version_hash( self )

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

	@staticmethod
	def saved_block_version_hash( saved_block_version ):
		"""
		Calculate and store the hash of the provided saved block version
		:type saved_block_version: SavedBlockVersion
		:return: sha256 digest
		"""
		block_object_json = saved_block_version.block_object_json
		serialized_block = json.dumps( block_object_json )

		saved_block_version.block_hash = hashlib.sha256(serialized_block).digest()

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )
		
	def __str__( self ):
		return self.id