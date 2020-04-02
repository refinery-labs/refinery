import os
import json
import shutil
import tempfile
import hashlib
import traceback
import uuid

from tornado import gen
from tornado.concurrent import run_on_executor, futures

from git import Repo

from models.project_versions import ProjectVersion
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

BLOCK_CODE_FILENAME = "block_code"

class RepoCompilationException(Exception):
	pass

class ProjectRepoAssistant:

	def __init__( self, logger ):
		self.logger = logger
		self.executor = futures.ThreadPoolExecutor( 60 )

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

		# set an id if not set
		if "id" not in block_config_json:
			block_config_json[ "id" ] = str(uuid.uuid4())

		return block_config_json

	@run_on_executor
	def compile_and_upsert_project_repo( self, dbsession, user_id, project_id, git_url ):
		try:
			return self._compile_and_upsert_project_repo(dbsession, user_id, project_id, git_url)
		except Exception as e:
			print traceback.format_exc()
		return None

	def _compile_and_upsert_project_repo( self, dbsession, user_id, project_id, git_url ):
		# TODO file reads and clones will be blocking

		git_repo = dbsession.query( GitRepo ).filter_by(
			project_id=project_id
		).first()

		repo_id = None
		if git_repo:
			repo_id = git_repo.id
		else:
			repo = GitRepo(project_id, git_url)
			dbsession.add(repo)
			dbsession.commit()

			repo_id = repo.id

		# TODO with context for better cleanup
		repo_dir = tempfile.mkdtemp()
		shutil.rmtree(repo_dir)

		repo = Repo.init(repo_dir)
		repo.git.remote("add", "origin", git_url)

		self.logger("starting clone")
		# TODO kill clone after timeout
		repo.git.pull("origin", "master", depth=1)

		self.logger("Cloned repo {} for project {}".format(git_url, project_id))

		# TODO check if clone was successful

		# TODO impose file size limits

		lambda_block_configs = []
		shared_file_configs = []
		shared_file_lookup = {}
		shared_file_links = []
		refinery_project = {
			"workflow_states": []
		}
		try:
			project_config_file_name = os.path.join(repo_dir, "project.json")
			if not os.path.exists(project_config_file_name):
				raise RepoCompilationException("unable to find project.json")

			with open(project_config_file_name, "rb") as opened_project_config:
				refinery_project.update(json.load(opened_project_config))

			shared_file_dir = os.path.join(repo_dir, "shared-files")
			if os.path.isdir(shared_file_dir):
				for shared_file_name in os.listdir(shared_file_dir):
					shared_file_path = os.path.join(shared_file_dir, shared_file_name)
					with open(shared_file_path, "rb") as opened_shared_file:

						shared_file_id = str(uuid.uuid4())
						shared_file_content = opened_shared_file.read()

						shared_file_configs.append({
							"body": shared_file_content,
							"version": "1.0.0",
							"type": "shared_file",
							"id": shared_file_id,
							"name": shared_file_name
						})

						shared_file_lookup[shared_file_path] = shared_file_id

			# TODO support other types besides lambdas
			lambda_dir = os.path.join(repo_dir, "lambda")
			if os.path.isdir(lambda_dir):
				for lambda_block_dir in os.listdir(lambda_dir):

					lambda_block_path = os.path.join(lambda_dir, lambda_block_dir)
					if not os.path.isdir(lambda_block_path):
						continue

					lambda_block_config = self.parse_lambda(git_url, lambda_block_path)
					if lambda_block_config is None:
						continue

					shared_files_path = os.path.join(lambda_block_path, "shared_files")
					if os.path.exists(shared_files_path):
						for shared_file_name in os.listdir(shared_files_path):

							shared_file_path = os.path.join(shared_files_path, shared_file_name)
							print shared_files_path, shared_file_lookup
							shared_file_uuid = shared_file_lookup.get(shared_file_path)
							if shared_file_uuid is None:
								self.logger("shared file was not found in shared file folder", "warning")
								continue

							shared_file_links.append({
								"node": lambda_block_config["id"],
								"version": "1.0.0",
								"file_id": shared_file_uuid,
								"path": "",
								"type": "shared_file_link",
								"id": str(uuid.uuid4())
							})

					lambda_block_configs.append(lambda_block_config)

			# merge compiled entities with project config
			refinery_project["workflow_states"].extend(lambda_block_configs)
			refinery_project.update({
				"workflow_files": shared_file_configs,
				"workflow_file_links": shared_file_links
			})
		except RepoCompilationException as e:
			self.logger(e, "error")
		finally:
			shutil.rmtree(repo_dir)

		self.logger("Project {} had {} blocks in {}".format(project_id, len(lambda_block_configs), git_url))

		# update saved blocks for git repo
		repo = dbsession.query( GitRepo ).filter_by(
			id=repo_id
		)
		repo.url = git_url

		dbsession.commit()

		print json.dumps(refinery_project, indent=2)
		return refinery_project
