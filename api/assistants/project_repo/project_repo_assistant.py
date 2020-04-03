import os
import traceback
import uuid

import yaml
import yaml.parser

from tornado.concurrent import run_on_executor, futures

from git import Repo, GitCommandError

from assistants.project_repo.clonable_repo import CloneableRepo, CloningRepoException

LANGUAGE_TO_EXT = {
	"nodejs8.10": "js",
	"nodejs10.16.3": "js",
	"php7.3": "php",
	"go1.12": "go",
	"python2.7": "py",
	"python3.6": "py",
	"ruby2.6.4": "rb"
}

PROJECT_CONFIG_FILENAME = "project.yaml"
PROJECT_LAMBDA_DIR = "lambda"
PROJECT_SHARED_FILES_DIR = "shared-files"

LAMBDA_CONFIG_FILENAME = "config.yaml"
LAMBDA_SHARED_FILES_DIR = "shared_files"

BLOCK_CODE_FILENAME = "block_code"


class RepoCompilationException(Exception):
	pass


class ProjectRepoAssistant:

	def __init__( self, logger ):
		self.logger = logger
		self.executor = futures.ThreadPoolExecutor( 60 )

	def get_file_contents(self, path, parse_yaml=False):
		# type: (str, bool) -> Union[str, dict, None]
		if not os.path.exists(path):
			self.logger("Unable to find file {}".format(path))
			return None

		try:
			# TODO set file size limit

			with open(path, "rb") as f:
				if parse_yaml:
					return yaml.safe_load(f)
				else:
					return f.read()
		except yaml.parser.ParserError as e:
			self.logger("Unable to parse {}".format(path))
			return None

	def load_lambda_code( self, lambda_path, block_config_yaml ):
		# type: (str, dict) -> Union[str, None]
		if "language" not in block_config_yaml:
			raise RepoCompilationException("No language set in block {}".format( lambda_path ) )
		block_config_language = block_config_yaml[ "language" ]

		ext = LANGUAGE_TO_EXT[ block_config_language ]
		block_code_filename = "{}.{}".format(BLOCK_CODE_FILENAME, ext)

		block_code_path = os.path.join( lambda_path, block_code_filename )
		return self.get_file_contents(block_code_path)

	def parse_lambda( self, lambda_path ):

		# load lambda's config
		block_config_path = os.path.join( lambda_path, LAMBDA_CONFIG_FILENAME )
		block_config_yaml = self.get_file_contents(block_config_path, parse_yaml=True)
		if block_config_yaml is None:
			raise RepoCompilationException("Unable to get get block config for {}".format( lambda_path ) )

		block_code = self.load_lambda_code(lambda_path, block_config_yaml)
		if block_code is None:
			raise RepoCompilationException("Unable to get get block code for {}".format( lambda_path ) )

		# set an id if not set
		block_config_id = str(uuid.uuid4())
		if "id" in block_config_yaml:
			block_config_id = block_config_yaml["id"]

		# merge loaded config with compiled values
		block_config_yaml.update({
			"id": block_config_id,
			"code": block_code
		})
		return block_config_yaml

	def load_lambda_block( self, lambda_block_path, shared_file_links, shared_file_lookup ):
		# type: (str, list, dict) -> dict
		lambda_block_config = self.parse_lambda(lambda_block_path)
		if lambda_block_config is None:
			raise RepoCompilationException("no config exists for lambda {}".format(lambda_block_path))

		# check for any files and create links between them and this lambda
		shared_files_path = os.path.join(lambda_block_path, LAMBDA_SHARED_FILES_DIR)
		if os.path.exists(shared_files_path):
			lambda_shared_file_links = self.create_shared_file_links(
				shared_files_path, shared_file_lookup, lambda_block_config["id"])
			shared_file_links.extend(lambda_shared_file_links)

		return lambda_block_config

	def load_lambda_blocks( self, lambda_dir, shared_file_links, shared_file_lookup ):
		# type: (str, list, dict) -> list
		lambda_block_configs = []
		for lambda_block_dir in os.listdir(lambda_dir):
			lambda_block_path = os.path.join(lambda_dir, lambda_block_dir)

			lambda_block_config = self.load_lambda_block(lambda_block_path, shared_file_links, shared_file_lookup)
			lambda_block_configs.append(lambda_block_config)

		return lambda_block_configs

	def load_shared_file_config( self, shared_file_name, shared_file_path ):
		with open(shared_file_path, "rb") as opened_shared_file:
			shared_file_content = opened_shared_file.read()

		shared_file_id = str(uuid.uuid4())

		return {
			"body": shared_file_content,
			"version": "1.0.0",
			"type": "shared_file",
			"id": shared_file_id,
			"name": shared_file_name
		}

	def load_shared_files( self, shared_file_dir ):
		shared_file_configs = []
		shared_file_lookup = {}
		for shared_file_name in os.listdir(shared_file_dir):
			shared_file_path = os.path.join(shared_file_dir, shared_file_name)
			shared_file_config = self.load_shared_file_config(shared_file_name, shared_file_path)

			shared_file_configs.append(shared_file_config)

			shared_file_lookup[shared_file_path] = shared_file_config["id"]

		return shared_file_configs, shared_file_lookup

	def create_shared_file_link( self, shared_file_lookup, lambda_id, shared_file_path ):
		if not os.path.islink(shared_file_path):
			raise RepoCompilationException(
				"shared file for lambda is not a symlink, must be symlink to a shared file in 'shared-files': {}".format(shared_file_path)
			)

		# follow shared file link and then resolve it to an absolute path
		shared_file_relative_path = os.readlink(shared_file_path)
		shared_file_dir = os.path.dirname(shared_file_path)
		followed_shared_file_path = os.path.abspath(
			os.path.join(shared_file_dir, shared_file_relative_path))

		shared_file_uuid = shared_file_lookup.get(followed_shared_file_path)
		if shared_file_uuid is None:
			raise RepoCompilationException(
				"shared file was not found in shared file folder: {}".format(followed_shared_file_path)
			)

		return {
			"node": lambda_id,
			"version": "1.0.0",
			"file_id": shared_file_uuid,
			"path": "",
			"type": "shared_file_link",
			"id": str(uuid.uuid4())
		}

	def create_shared_file_links( self, shared_files_path, shared_file_lookup, lambda_id ):
		shared_file_links = []
		for shared_file_name in os.listdir(shared_files_path):
			shared_file_path = os.path.join(shared_files_path, shared_file_name)

			shared_file_link = self.create_shared_file_link(shared_file_lookup, lambda_id, shared_file_path)
			shared_file_links.append(shared_file_link)

		return shared_file_links

	def load_project_from_dir( self, repo_dir ):
		# type: (str) -> dict
		refinery_project = {
			"workflow_states": []
		}

		lambda_block_configs = []
		shared_file_configs = []
		shared_file_lookup = {}
		shared_file_links = []

		project_config_file_name = os.path.join(repo_dir, PROJECT_CONFIG_FILENAME)
		if not os.path.exists(project_config_file_name):
			raise RepoCompilationException("unable to find project.yaml")

		with open(project_config_file_name, "rb") as opened_project_config:
			refinery_project.update(yaml.safe_load(opened_project_config))

		shared_file_dir = os.path.join(repo_dir, PROJECT_SHARED_FILES_DIR)
		if os.path.isdir(shared_file_dir):
			shared_file_configs, shared_file_lookup = self.load_shared_files(shared_file_dir)

		lambda_dir = os.path.join(repo_dir, PROJECT_LAMBDA_DIR)
		if os.path.isdir(lambda_dir):
			# shared_file_links is a mutable list which is populated by each lambda's shared files
			lambda_block_configs = self.load_lambda_blocks(lambda_dir, shared_file_links, shared_file_lookup)

		# merge compiled entities with project config
		refinery_project["workflow_states"].extend(lambda_block_configs)
		refinery_project.update({
			"workflow_files": shared_file_configs,
			"workflow_file_links": shared_file_links
		})
		return refinery_project

	@run_on_executor
	def compile_and_upsert_project_repo( self, project_id, git_url ):
		# type: (str, str) -> (Union[dict, None], str)
		try:
			return self._compile_and_upsert_project_repo(project_id, git_url), ""
		except RepoCompilationException as e:
			self.logger("An error occurred while compiling repository: {}".format(e), "error")
			return None, str(e)
		except GitCommandError as e:
			self.logger("An error occurred while cloning repository: {}".format(e), "error")
			return None, str(e)
		except CloningRepoException as e:
			self.logger("An error occurred while cloning repository: {}".format(e), "error")
			return None, str(e)
		except Exception as e:
			# TODO remove this print
			print traceback.format_exc()
			return None, str(e)

	def _compile_and_upsert_project_repo( self, project_id, git_url ):
		with CloneableRepo(git_url) as repo_dir:
			self.logger("Cloned repo {} for project {}".format(git_url, project_id))

			refinery_project = self.load_project_from_dir(repo_dir)
			refinery_project["project_id"] = project_id

			return refinery_project
