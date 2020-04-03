import shutil
import tempfile

from git import Repo, RemoteProgress


class CloningRepoException(Exception):
	pass


class CloneableRepoProgress(RemoteProgress):
	succeeded = False
	last_op_code = 0

	def update(self, op_code, cur_count, max_count=None, message=''):
		# do something with max_count?
		# if max_count > 1:
		#   raise CloningRepoException("too many objects to clone")

		if op_code & RemoteProgress.END == RemoteProgress.END:
			self.succeeded = True
		self.last_op_code = op_code


class CloneableRepo(object):
	def __init__(self, git_url):
		self.git_url = git_url
		self.repo_dir = tempfile.mkdtemp()
		shutil.rmtree(self.repo_dir)

	def __enter__(self):
		clonable_repo_progress = CloneableRepoProgress()

		# TODO test if this timeout works
		multi_options = [
			"--depth 1"
		]
		env = {
			"GIT_HTTP_LOW_SPEED_LIMIT": "1000",
			"GIT_HTTP_LOW_SPEED_TIME": "600"
		}
		Repo.clone_from(self.git_url, self.repo_dir, progress=clonable_repo_progress, env=env, multi_options=multi_options)

		if not clonable_repo_progress.succeeded:
			raise CloningRepoException("failed to clone repo, last executed op code: {}".format(clonable_repo_progress.last_op_code))

		return self.repo_dir

	def __exit__(self, type, value, traceback):
		shutil.rmtree(self.repo_dir)
