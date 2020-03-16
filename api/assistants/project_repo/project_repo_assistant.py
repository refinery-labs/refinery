import os
import json
import shutil
import tempfile
import hashlib
from git import Repo

from models.saved_block import SavedBlock
from models.saved_block_version import SavedBlockVersion
from models.git_repo import GitRepo

LANGUAGE_TO_EXT = {
	"nodejs8.10": "js",
	"nodejs10.16.3": "js",
	"php7.3": "php",
	"go1.12": "go",
	"python2.7": "py",
	"python3.6": "py",
	"ruby2.6.4": "rb"
}

BLOCK_CODE_FILENAME = "block-code"

class ProjectRepoAssistant:

	def __init__( self, logger, local_tasks ):
		self.logger = logger
		self.local_tasks = local_tasks

	def clear_existing_git_saved_blocks( self, dbsession, project_id ):
		git_repo = dbsession.query( GitRepo ).filter_by(
			project_id=project_id
		).first()

		if not git_repo:
			# repo does not exist
			return None

		for block in git_repo.blocks:
			dbsession.delete(block)

		return git_repo.id

	def create_git_saved_block( self, dbsession, user_id, block_config, shared_files=[] ):
		saved_block = SavedBlock()

		saved_block.share_status = "GIT"

		saved_block.user_id = user_id
		saved_block.name = block_config[ "name" ]
		saved_block.type = "lambda"
		saved_block.description = "" if "description" not in block_config else ""

		dbsession.commit()

		# Get the latest saved block version
		saved_block_latest_version = dbsession.query( SavedBlockVersion ).filter_by(
			saved_block_id=saved_block.id
		).order_by( SavedBlockVersion.version.desc() ).first()

		# If we have an old version bump it
		block_version = 0
		if saved_block_latest_version:
			block_version = saved_block_latest_version.version + 1

		# Now we add the block version
		new_saved_block_version = SavedBlockVersion()
		new_saved_block_version.saved_block_id = saved_block.id
		new_saved_block_version.version = block_version
		new_saved_block_version.block_object_json = block_config
		new_saved_block_version.shared_files = shared_files

		saved_block.versions.append(
			new_saved_block_version
		)

		dbsession.add( saved_block )
		dbsession.commit()

	def parse_code_block( self, git_url, code_block_dir ):
		def get_file_contents(path, parse_json=False):
			if not os.path.exists(path):
				self.logger("Unable to find file {} for block: {} in {}".format(path, code_block_dir, git_url))
				return

			try:
				with open(path, "rb") as f:
					if parse_json:
						return json.load(f)
					else:
						return f.read()
			except ValueError as e:
				self.logger("Unable to parse {} for block: {} in {}".format(path, code_block_dir, git_url))
				return

		block_config_path = os.path.join(code_block_dir, "config.json")
		block_config_json = get_file_contents(block_config_path, parse_json=True)

		if "language" not in block_config_json:
			self.logger("No language set in block {} in {}".format(code_block_dir, git_url))
			return

		ext = LANGUAGE_TO_EXT[ block_config_json[ "language" ] ]
		block_code_filename = "{}.{}".format(BLOCK_CODE_FILENAME, ext)

		block_code_path = os.path.join(code_block_dir, block_code_filename)
		block_code = get_file_contents(block_code_path)

		block_config_json[ "code" ] = block_code

		return block_config_json

	def upsert_blocks_from_repo( self, dbsession, user_id, project_id, git_url ):
		repo_id = self.clear_existing_git_saved_blocks(dbsession, project_id)

		if not repo_id:
			repo = GitRepo(project_id, git_url)
			dbsession.add()
			dbsession.commit()

			repo_id = repo.id

		repo_dir = tempfile.mkdtemp()
		git_repo = Repo.clone_from(git_url, repo_dir)

		code_block_dirs = [d for d in os.listdir(repo_dir) if os.path.isdir(d)]

		block_configs = []
		try:
			for code_block_dir in code_block_dirs:
				block_config = self.parse_code_block(git_url, code_block_dir)
				block_config.append(block_config)
		finally:
			shutil.rmtree(repo_dir)

		saved_blocks = []
		for block_config in block_configs:
			block_config_str = json.dumps(block_config)
			block_config_hash = hashlib.sha256(block_config_str).digest()

			existing_block = dbsession.query( SavedBlockVersion ).filter_by(
				block_hash=block_config_hash
			)

			# if we find a block that exactly matches the one about to be created
			# then we do not need to recreate it
			if existing_block:
				continue

			# TODO figure out shared files
			shared_files = []
			saved_block = self.create_git_saved_block(dbsession, user_id, block_config, shared_files)
			saved_blocks.append(saved_block)

		# update saved blocks for git repo
		repo = dbsession.query( GitRepo ).filter_by(
			id=repo_id
		)
		repo.blocks = saved_blocks

		dbsession.commit()
