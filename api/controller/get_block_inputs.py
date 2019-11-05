from tornado import gen
from controller.base import BaseHandler
from jsonschema import validate as validate_schema

from models.initiate_database import *

from utils.cached_block_io import get_cached_block_data_for_block_id

from utils.general import logit

class GetBlockInputs( BaseHandler ):
	@gen.coroutine
	def post( self ):
		"""
		Returns possible block inputs from past cached values from editor runs/deployment logs.
		"""
		schema = {
			"type": "object",
			"properties": {
				"block_ids": {
					"type": "array",
					"items": {
						"type": "string"
					},
					"minItems": 1,
					"maxItems": 1000
				},
				"io_type": {
					"type": "string",
					"enum": [ "RETURN", "INPUT" ]
				},
				"origin": {
					"type": "string",
					"enum": [ "DEPLOYMENT", "EDITOR" ]
				}
			},
			"required": [
				"block_ids"
			]
		}
		
		validate_schema( self.json, schema )

		if not "io_type" in self.json:
			self.json[ "io_type" ] = None

		if not "origin" in self.json:
			self.json[ "origin" ] = None

		cached_block_data = yield get_cached_block_data_for_block_id(
			self.get_authenticated_user_id(),
			self.json[ "block_ids" ],
			self.json[ "io_type" ],
			self.json[ "origin" ]
		)

		self.write({
			"success": True,
			"results": cached_block_data
		})