import os
import json
import shutil
import tempfile
import hashlib

from tornado import gen
from tornado.concurrent import run_on_executor, futures

from git import Repo

from models.saved_block import SavedBlock
from models.saved_block_version import SavedBlockVersion
from models.git_repo import GitRepo
from models.git_block import GitBlock

LANGUAGE_TO_EXT = {
	"nodejs8.10": "js",
	"nodejs10.16.3": "js",
	"php7.3": "php",
	"go1.12": "go",
	"python2.7": "py",
	"python3.6": "py",
	"ruby2.6.4": "rb"
}

BLOCK_CODE_FILENAME = "block_code"

class ProjectRepoAssistant:

	def __init__( self, logger ):
		self.logger = logger
		self.executor = futures.ThreadPoolExecutor( 60 )

	def clear_existing_git_saved_blocks( self, dbsession, project_id ):
		git_repo = dbsession.query( GitRepo ).filter_by(
			project_id=project_id
		).first()

		if not git_repo:
			# repo does not exist
			return None

		for block in git_repo.blocks:
			dbsession.delete(block)
			dbsession.commit()

		return git_repo.id

	def create_new_saved_block( self, user_id, block_config ):
		saved_block = SavedBlock()

		saved_block.share_status = "GIT"

		saved_block.user_id = user_id
		saved_block.name = block_config[ "name" ]
		saved_block.type = "lambda"
		saved_block.description = "" if "description" not in block_config else ""

		return saved_block

	def create_new_saved_block_version( self, dbsession, saved_block_id, block_config, shared_files ):
		# Get the latest saved block version
		saved_block_latest_version = dbsession.query( SavedBlockVersion ).filter_by(
			saved_block_id=saved_block_id
		).order_by( SavedBlockVersion.version.desc() ).first()

		# If we have an old version bump it
		block_version = 0
		if saved_block_latest_version:
			block_version = saved_block_latest_version.version + 1

		# Now we add the block version
		new_saved_block_version = SavedBlockVersion()
		new_saved_block_version.saved_block_id = saved_block_id
		new_saved_block_version.version = block_version
		new_saved_block_version.block_object_json = block_config
		new_saved_block_version.shared_files = shared_files

		return new_saved_block_version

	def create_git_saved_block( self, dbsession, user_id, repo_id, block_config, block_config_hash, shared_files=[] ):

		saved_block = dbsession.query( SavedBlock ).filter_by(
			name=block_config[ "name" ]
		).first()
		if not saved_block:
			saved_block = self.create_new_saved_block(user_id, block_config)

		new_saved_block_version = self.create_new_saved_block_version(
			dbsession, saved_block.id, block_config, shared_files)

		saved_block.versions.append(
			new_saved_block_version
		)

		dbsession.add( saved_block )
		dbsession.commit()

		git_block = GitBlock(repo_id, saved_block.id)

		dbsession.add( git_block )
		dbsession.commit()

		return git_block

	def parse_lambda( self, git_url, lambda_path ):
		def get_file_contents(path, parse_json=False):
			if not os.path.exists(path):
				self.logger("Unable to find file {} for block: {} in {}".format( path, lambda_path, git_url ) )
				return

			try:
				with open(path, "rb") as f:
					if parse_json:
						return json.load(f)
					else:
						return f.read()
			except ValueError as e:
				self.logger("Unable to parse {} for block: {} in {}".format( path, lambda_path, git_url ) )
				return None

		block_config_path = os.path.join( lambda_path, "config.json" )
		block_config_json = get_file_contents(block_config_path, parse_json=True)

		if block_config_json is None:
			self.logger("Unable to get get block config for {} in {}".format( lambda_path, git_url ) )
			return None

		if "language" not in block_config_json:
			self.logger("No language set in block {} in {}".format( lambda_path, git_url ) )
			return

		ext = LANGUAGE_TO_EXT[ block_config_json[ "language" ] ]
		block_code_filename = "{}.{}".format(BLOCK_CODE_FILENAME, ext)

		block_code_path = os.path.join( lambda_path, block_code_filename )
		block_code = get_file_contents(block_code_path)

		if block_code is None:
			self.logger("Unable to get get block code for {} in {}".format( lambda_path, git_url ) )
			return None

		block_config_json[ "code" ] = block_code

		return block_config_json

	@run_on_executor
	@gen.coroutine
	def upsert_blocks_from_repo( self, dbsession, user_id, project_id, git_url ):
		repo_id = self.clear_existing_git_saved_blocks(dbsession, project_id)

		if not repo_id:
			repo = GitRepo(project_id, git_url)
			dbsession.add(repo)
			dbsession.commit()

			repo_id = repo.id

		# TODO with context for better cleanup
		repo_dir = tempfile.mkdtemp()
		shutil.rmtree(repo_dir)

		repo = Repo.init(repo_dir)
		repo.git.remote("add", "origin", git_url)

		# TODO kill clone after timeout
		repo.git.pull("origin", "master", depth=1)

		self.logger("Cloned repo {} for project {}".format(git_url, project_id))

		# TODO check if clone was successful

		lambda_block_configs = []
		try:
			# TODO support other types besides lambdas
			lambda_dir = os.path.join(repo_dir, "lambda")
			for lambda_block_dir in os.listdir(lambda_dir):

				lambda_block_path = os.path.join(lambda_dir, lambda_block_dir)
				if not os.path.isdir(lambda_block_path):
					continue

				lambda_block_config = self.parse_lambda(git_url, lambda_block_path)
				if lambda_block_config is None:
					continue

				lambda_block_configs.append(lambda_block_config)
		finally:
			shutil.rmtree(repo_dir)

		self.logger("Project {} had {} blocks in {}".format(project_id, len(lambda_block_configs), git_url))

		git_blocks = []
		for lambda_block_config in lambda_block_configs:
			block_config_str = json.dumps(lambda_block_config)
			block_config_hash = bytearray(hashlib.sha256(block_config_str).digest())

			existing_block = dbsession.query( SavedBlockVersion ).filter_by(
				block_hash=block_config_hash
			).first()

			# if we find a block that exactly matches the one about to be created
			# then we do not need to recreate it
			# TODO maybe just pass IDs to prevent race conditions?
			if existing_block:
				git_blocks.append(existing_block)

			# TODO figure out shared files
			shared_files = []
			git_block = self.create_git_saved_block(dbsession, user_id, repo_id, lambda_block_config, shared_files)
			git_blocks.append(git_block)

		# update saved blocks for git repo
		repo = dbsession.query( GitRepo ).filter_by(
			id=repo_id
		)
		repo.blocks = git_blocks
		repo.url = git_url

		dbsession.commit()
