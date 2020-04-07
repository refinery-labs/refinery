import json

from tornado import gen, httpclient
from tornado.httpclient import HTTPError

from models.github_webooks import GithubWebhook


class GithubRepoManager:
	_API_BASE_HEADERS = {
		"Accept": "application/json",
		"User-Agent": "Tornado OAuth",
		"Authorization": "token {access_token}"
	}
	_REPO_WEBHOOKS_URL = "https://api.github.com/repos/{owner}/{repo}/hooks"
	_EDIT_REPO_WEBHOOK_URL = "https://api.github.com/repos/{owner}/{repo}/hooks/{hook_id}"

	def __init__(self, logger, webhook_url):
		self.logger = logger
		self.webhook_url = webhook_url
		self.http = httpclient.AsyncHTTPClient()

	def webhook_url( self ):
		return "{}/api/v1/github/webhook".format(self.webhook_url)

	def _format_base_headers( self, access_token ):
		base_headers = self._API_BASE_HEADERS
		base_headers["Authorization"] = base_headers["Authorization"].format(access_token=access_token)
		return base_headers

	@gen.coroutine
	def list_repo_webhooks( self, access_token, owner, repo ):
		try:
			return self._list_repo_webhooks(access_token, owner, repo)
		except Exception as e:
			print e

	def _list_repo_webhooks( self, access_token, owner, repo ):
		# List hooks: https://developer.github.com/v3/repos/hooks/#list-hooks
		# GET /repos/:owner/:repo/hooks

		try:
			response = yield self.http.fetch(
				self._REPO_WEBHOOKS_URL.format(
					owner=owner,
					repo=repo
				),
				method='GET',
				headers=self._format_base_headers(access_token)
			)
		except HTTPError as e:
			raise Exception( "Unable to install repo commit webhook: {}".format(e) )

		webhooks = json.loads(response.body)
		raise gen.Return(webhooks)

	@gen.coroutine
	def install_repo_webhook(self, access_token, owner, repo, hook_id=0):
		try:
			return self._install_repo_webhook(access_token, owner, repo, hook_id)
		except Exception as e:
			print e

	def _install_repo_webhook( self, access_token, owner, repo, hook_id ):
		# Create a hook: https://developer.github.com/v3/repos/hooks/#create-a-hook
		# POST /repos/:owner/:repo/hooks

		# Edit a hook: https://developer.github.com/v3/repos/hooks/#edit-a-hook
		# PATCH /repos/:owner/:repo/hooks/:hook_id

		github_webhook = GithubWebhook()

		webhook_request = {
			"name": "web",
			"events": ["push"],
			"active": True,
			"config": {
				"url": self.webhook_url(),
				"content_type": "json",
				"secret": github_webhook.secret,
				"insecure_ssl": 0
			}
		}

		if hook_id == 0:
			url = self._REPO_WEBHOOKS_URL.format(
				owner=owner,
				repo=repo
			)
		else:
			url = self._EDIT_REPO_WEBHOOK_URL.format(
				owner=owner,
				repo=repo,
				hook_id=hook_id
			)

		try:
			response = yield self.http.fetch(
				url,
				body=json.dumps(webhook_request),
				method='POST' if hook_id == 0 else 'PATCH',
				headers=self._format_base_headers(access_token)
			)
		except HTTPError as e:
			raise Exception( "Unable to install repo commit webhook: {}".format(e) )

		response_json = json.loads(response.body)

		github_webhook.webhook_id = response_json["id"]
		raise gen.Return(github_webhook)
