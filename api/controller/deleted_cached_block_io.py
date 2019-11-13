from tornado import gen
from controller.base import BaseHandler
from jsonschema import validate as validate_schema

from models.initiate_database import *

from utils.cached_block_io import delete_cached_block_io_by_id

from utils.general import logit

class DeleteCachedBlockIO( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Deletes cached block IO by ID
		"""
		schema = {
			"type": "object",
			"properties": {
				"cached_block_input_id": {
					"type": "string"
				}
			},
			"required": [
				"cached_block_input_id"
			]
		}
		
		validate_schema( self.json, schema )

		cached_block_data = yield delete_cached_block_io_by_id(
			self.get_authenticated_user_id(),
			self.json[ "cached_block_input_id" ]
		)

		self.write({
			"success": True
		})