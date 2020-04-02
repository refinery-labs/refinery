from tornado import gen, httpclient
from tornado.httpclient import HTTPError


class GithubRepoManager:
	_API_BASE_HEADERS = {
		"Accept": "application/json",
		"User-Agent": "Tornado OAuth",
		"Authorization": "token {access_token}"
	}
	_REPO_WEBHOOKS_URL = "https://api.github.com/repos/{owner}/{repo}/hooks?access_token="

	def __init__(self, logger):
		self.logger = logger
		self.http = httpclient.AsyncHTTPClient()

	def _format_base_headers( self, access_token ):
		base_headers = self._API_BASE_HEADERS
		base_headers["Authorization"] = base_headers["Authorization"].format(access_token=access_token)
		return base_headers

	@gen.coroutine
	def install_repo_webhook(self, access_token, owner, repo):
		# Create a hook: https://developer.github.com/v3/repos/hooks/#create-a-hook
		# POST /repos/:owner/:repo/hooks

		try:
			response = yield self.http.fetch(
				self._REPO_WEBHOOKS_URL,
				method='POST',
				headers=self._format_base_headers(access_token)
			)
		except HTTPError as e:
			raise Exception( "Unable to install repo commit webhook", data=e )

		print response

		raise gen.Return(True)
