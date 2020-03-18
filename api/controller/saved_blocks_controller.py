import uuid

from tornado import gen
from jsonschema import validate as validate_schema

from controller.base import BaseHandler
from controller.decorators import authenticated
from utils.general import logit
from utils.locker import  AcquireFailure

from models.initiate_database import *
from models.saved_block import SavedBlock
from models.saved_block_version import SavedBlockVersion
from models.git_repo import GitRepo
from models.git_block import GitBlock

class SavedBlocksCreate( BaseHandler ):
	@authenticated
	def post( self ):
		"""
		Create a saved block to import into other projects.
		"""
		schema = {
			"type": "object",
			"properties": {
				"id": {
					"type": "string"
				},
				"description": {
					"type": "string"
				},
				"block_object": {
					"type": "object",
					"properties": {
						"name": {
							"type": "string",
						},
						"type": {
							"type": "string",
						}
					},
					"required": [
						"name",
						"type"
					]
				},
				"version": {
					"type": "integer",
				},
				"share_status": {
					"type": "string",
					"enum": [
						"PRIVATE",
						"PUBLISHED"
					]
				},
				"save_type": {
					"type": "string",
					"enum": [
						"FORK",
						"CREATE",
						"UPDATE"
					]
				},
				"shared_files": {
					"type": "array",
					"default": [],
				}
			},
			"required": [
				"block_object"
			]
		}

		validate_schema( self.json, schema )
		logit( "Saving Block data..." )

		saved_block = None

		block_version = 1

		# Default to "UPDATE" for now to avoid issues with user pages not reloaded
		block_save_type = "UPDATE"
		if "save_type" in self.json:
			block_save_type = self.json[ "save_type" ]

		# Do not search for an existing block if we are forking, only on UPDATE
		if "id" in self.json and block_save_type == "UPDATE":
			saved_block = self.dbsession.query( SavedBlock ).filter_by(
				user_id=self.get_authenticated_user_id(),
				id=self.json[ "id" ]
			).first()

			# If we didn't find the block return an error
			if not saved_block:
				self.write({
					"success": False,
					"code": "SAVED_BLOCK_NOT_FOUND",
					"msg": "The saved block you're attempting to save could not be found!"
				})
				return

			block_version = saved_block.versions

		# If the block ID is not specified then we are creating
		# a new saved block in the database.
		if not saved_block:
			saved_block = SavedBlock()
			saved_block.share_status = "PRIVATE"

		saved_block.user_id = self.get_authenticated_user_id()
		saved_block.name = self.json[ "block_object" ][ "name" ]
		saved_block.type = self.json[ "block_object" ][ "type" ]
		saved_block.description = ""

		if "description" in self.json:
			saved_block.description = self.json[ "description" ]

		new_share_status = saved_block.share_status

		if "share_status" in self.json:
			new_share_status = self.json[ "share_status" ]

		# Ensure that a user can only make a PRIVATE saved block PUBLISHER
		# We don't allow the other way around
		if saved_block.share_status == "PUBLISHED" and new_share_status == "PRIVATE":
			self.write({
				"success": False,
				"code": "CANNOT_UNPUBLISH_SAVED_BLOCKS",
				"msg": "You cannot un-publish an already-published block!"
			})
			return

		saved_block.share_status = new_share_status

		self.dbsession.commit()

		# Get the latest saved block version
		saved_block_latest_version = self.dbsession.query( SavedBlockVersion ).filter_by(
			saved_block_id=saved_block.id
		).order_by( SavedBlockVersion.version.desc() ).first()

		# If we have an old version bump it
		if saved_block_latest_version:
			block_version = saved_block_latest_version.version + 1

		# Now we add the block version
		new_saved_block_version = SavedBlockVersion()
		new_saved_block_version.saved_block_id = saved_block.id
		new_saved_block_version.version = block_version
		new_saved_block_version.block_object_json = self.json[ "block_object" ]
		new_saved_block_version.shared_files = self.json[ "shared_files" ]

		saved_block.versions.append(
			new_saved_block_version
		)

		self.dbsession.add( saved_block )
		self.dbsession.commit()

		self.write({
			"success": True,
			"block": {
				"id": saved_block.id,
				"description": saved_block.description,
				"name": saved_block.name,
				"share_status": new_share_status,
				"type": saved_block.type,
				"block_object": new_saved_block_version.block_object_json,
				"version": new_saved_block_version.version,
				"timestamp": new_saved_block_version.timestamp
			}
		})


def generate_saved_block_filters(share_status, block_language, search_string, authenticated_user_id, project_id):
	# filters to apply when searching for saved blocks
	saved_block_filters = []

	if search_string != "":
		saved_block_filters.append(
			sql_or(
				SavedBlock.name.ilike( "%" + search_string + "%" ),
				SavedBlock.description.ilike( "%" + search_string + "%" ),
			)
		)

	if share_status == "GIT":
		saved_block_filters.append(
			GitRepo.project_id == project_id
		)

	if share_status == "PRIVATE":
		if authenticated_user_id == None:
			# Return nothing because we're not logged in, so there can't possibly be private blocks to search.
			return [False]

		# Default is to just search your own saved blocks
		saved_block_filters.append(
			SavedBlock.share_status == share_status
		)
		saved_block_filters.append(
			SavedBlock.user_id == authenticated_user_id
		)

	if share_status == "PUBLISHED":
		saved_block_filters.append(
			SavedBlock.share_status == "PUBLISHED"
		)

	if block_language != "":
		saved_block_filters.append(
			SavedBlockVersion._block_object_json[ "language" ].astext == block_language
		)

	return saved_block_filters

class SavedBlockSearch( BaseHandler ):
	def post( self ):
		"""
		Free text search of saved Lambda, returns matching results.
		"""
		schema = {
			"type": "object",
			"properties": {
				"search_string": {
					"type": "string",
				},
				"share_status": {
					"type": "string",
					"enum": [
						"PRIVATE",
						"PUBLISHED",
						"GIT"
					]
				},
				"language": {
					"type": "string",
				},
				"project_id": {
					"type": "string"
				}
			},
			"required": [
				"search_string",
			]
		}

		validate_schema( self.json, schema )

		logit( "Searching saved Blocks..." )

		share_status = "PRIVATE"
		block_language = ""
		search_string = ""
		project_id = ""

		if "share_status" in self.json:
			share_status = self.json[ "share_status" ]

		if "language" in self.json:
			block_language = self.json[ "language" ]

		if "search_string" in self.json:
			search_string = self.json[ "search_string" ]

		if "project_id" in self.json:
			project_id = self.json[ "project_id" ]

			# Ensure user is owner of the project
			if not self.is_owner_of_project( project_id ):
				self.write({
					"success": False,
					"code": "ACCESS_DENIED",
					"msg": "You do not have privileges to access that project version!",
				})
				raise gen.Return()

		authenticated_user_id = self.get_authenticated_user_id()

		saved_block_filters = generate_saved_block_filters(
			share_status, block_language, search_string, authenticated_user_id, project_id
		)

		# TODO: Add pagination and limit the number of results returned.
		saved_blocks_query = self.dbsession.query( SavedBlock ).distinct(SavedBlock.id).join(
			# join the saved block and version tables based on IDs
			SavedBlockVersion, SavedBlock.id == SavedBlockVersion.saved_block_id
		)

		if share_status == "GIT":
			saved_blocks_query = saved_blocks_query.join(
				GitBlock, SavedBlock.id == GitBlock.saved_block_id
			).join(
				GitRepo, GitBlock.repo_id == GitRepo.id
			)

		saved_blocks = saved_blocks_query.filter(
			*saved_block_filters
		).all()

		return_list = []

		for saved_block in saved_blocks:
			# Get the latest saved block version
			saved_block_latest_version = self.dbsession.query( SavedBlockVersion ).filter_by(
				saved_block_id=saved_block.id
			).order_by( SavedBlockVersion.version.desc() ).first()

			block_object = saved_block_latest_version.block_object_json
			block_object[ "id" ] = str( uuid.uuid4() )

			return_list.append({
				"id": saved_block.id,
				"description": saved_block.description,
				"name": saved_block.name,
				"share_status": saved_block.share_status,
				"type": saved_block.type,
				"block_object": block_object,
				"version": saved_block_latest_version.version,
				"shared_files": saved_block_latest_version.shared_files,
				"timestamp": saved_block_latest_version.timestamp,
			})

		self.write({
			"success": True,
			"results": return_list
		})


class SavedBlockStatusCheck( BaseHandler ):
	@authenticated
	def post( self ):
		"""
		Given a list of blocks, return metadata about them.
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
					"maxItems": 100
				}
			},
			"required": [
				"block_ids",
			]
		}

		validate_schema( self.json, schema )

		logit( "Fetching saved Block metadata..." )

		# Search through all published saved blocks
		saved_blocks = self.dbsession.query( SavedBlock ).filter(
			SavedBlock.id.in_(self.json[ "block_ids" ]),
			sql_or(
				SavedBlock.user_id == self.get_authenticated_user_id(),
				SavedBlock.share_status == "PUBLISHED"
			)
		).limit(100).all()

		return_list = []

		for saved_block in saved_blocks:
			# Get the latest saved block version
			saved_block_latest_version = self.dbsession.query( SavedBlockVersion ).filter_by(
				saved_block_id=saved_block.id
			).order_by( SavedBlockVersion.version.desc() ).first()

			block_object = saved_block_latest_version.block_object_json

			return_list.append({
				"id": saved_block.id,
				"is_block_owner": saved_block.user_id == self.get_authenticated_user_id(),
				"description": saved_block.description,
				"name": saved_block.name,
				"share_status": saved_block.share_status,
				"version": saved_block_latest_version.version,
				"timestamp": saved_block_latest_version.timestamp,
				"block_object": block_object,
			})

		self.write({
			"success": True,
			"results": return_list
		})


class SavedBlockDelete( BaseHandler ):
	@authenticated
	def delete( self ):
		"""
		Delete a saved Block
		"""
		schema = {
			"type": "object",
			"properties": {
				"id": {
					"type": "string",
				}
			},
			"required": [
				"id"
			]
		}

		validate_schema( self.json, schema )

		logit( "Deleting Block data..." )

		saved_block = self.dbsession.query( SavedBlock ).filter_by(
			user_id=self.get_authenticated_user_id(),
			id=self.json[ "id" ]
		).first()

		if saved_block.share_status == "PUBLISHED":
			self.write({
				"success": False,
				"msg": "You cannot delete an already-published block!",
				"code": "ERROR_CANNOT_DELETE_PUBLISHED_BLOCK"
			})
			return

		if saved_block == None:
			self.write({
				"success": False,
				"msg": "This block does not exist!",
				"code": "BLOCK_NOT_FOUND"
			})
			return

		self.dbsession.delete(saved_block)
		self.dbsession.commit()

		self.write({
			"success": True
		})

class SavedBlockImport( BaseHandler ):
	def initialize( self, repo_assistant ):
		super( SavedBlockImport, self ).initialize()

		self.repo_assistant = repo_assistant

	@authenticated
	@gen.coroutine
	def post( self ):
		"""
		Import saved Blocks from configured repository
		"""
		schema = {
			"type": "object",
			"properties": {
				"project_id": {
					"type": "string",
				},
				"project_repo": {
					"type": "string"
				}
			},
			"required": [
				"project_id",
				"project_repo"
			]
		}

		validate_schema( self.json, schema )

		logit( "Importing saved blocks for project: " + self.json[ "project_id" ] )

		project_id = self.json[ "project_id" ]
		project_repo = self.json[ "project_repo" ]

		# Ensure user is owner of the project
		if not self.is_owner_of_project( project_id ):
			self.write({
				"success": False,
				"code": "ACCESS_DENIED",
				"msg": "You do not have privileges to access that project version!",
			})
			raise gen.Return()

		user_id = self.get_authenticated_user_id()

		lock_id = "git_block_import_" + project_id
		lock = self.task_locker.lock(self.dbsession, lock_id)
		try:
			with lock:
				# do not wait for upsert to complete, this will run in the background
				self.repo_assistant.upsert_blocks_from_repo(self.dbsession, user_id, project_id, project_repo)
		except AcquireFailure:
			logit( "unable to acquire git block lock for " + project_id )
			self.write({
				"success": False,
				"code": "GIT_BLOCK_UPSERT_LOCK_FAILURE",
				"msg": "Importing git blocks for this project is already in progress",
			})
			raise gen.Return()

		self.write({
			"success": True
		})

