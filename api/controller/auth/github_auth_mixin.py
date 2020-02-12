# coding: utf-8
#
# Copyright (c) Alexandr Emelin. BSD license.
# All rights reserved.
#
"""
class GithubAuthHandler(BaseHandler, auth.GithubMixin):

    x_site_token = "application"

    @tornado.web.asynchronous
    def get(self):
        redirect_uri = "{0}://{1}{2}".format(
            self.request.protocol,
            self.request.host,
            self.reverse_url("auth_github")
        )
        params = {
            "redirect_uri": redirect_uri,
            "client_id":    self.opts["github_client_id"],
            "state":        self.x_site_token
        }

        code = self.get_argument("code", None)

        # Seek the authorization
        if code:
            # For security reason, the state value (cross-site token) will be
            # retrieved from the query string.
            params.update({
                "client_secret": self.opts["github_client_secret"],
                "success_callback": self._on_auth,
                "error_callback": self._on_error,
                "code":  code,
                "state": self.get_argument("state", None)
            })
            self.get_authenticated_user(**params)
            return

        # Redirect for user authentication
        self.get_authenticated_user(**params)

    @coroutine
    def _on_auth(self, user, access_token=None):
        if not user:
            raise tornado.web.HTTPError(500, "Github auth failed")
        user_data, error = yield storage.get_or_create_user(
            self.db,
            user["email"]
        )
        if error:
            raise tornado.web.HTTPError(500, "Auth failed")
        self.set_secure_cookie("user", tornado.escape.json_encode(user_data))
        self.redirect(self.reverse_url("main"))

    def _on_error(self, code, body=None, error=None):
        if body:
            logging.error(body)
        if error:
            logging.error(error)
        raise tornado.web.HTTPError(500, "Github auth failed")
"""
import os

from tornado.escape import json_decode
import codecs
import json
import re

from controller.base import BaseHandler

try:
	from urllib import urlencode
except ImportError:
	# python 3
	from urllib.parse import urlencode

from tornado import httpclient
from tornado.auth import OAuth2Mixin


class GithubMixin( BaseHandler, OAuth2Mixin ):
	"""GitHub OAuth2 Authentication

	To authenticate with GitHub, first register your application at
	https://github.com/settings/applications/new to get the client ID and
	secret.
	"""

	_API_BASE_HEADERS = {
		"Accept": "application/json",
		"User-Agent": "Tornado OAuth"
	}
	_OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
	_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
	_OAUTH_USER_URL = "https://api.github.com/user?access_token="

	def generate_state_token( self, deterministic_value_override=None ):
		# Allows for testing
		if deterministic_value_override:
			return deterministic_value_override

		return os.urandom( 16 ).encode( "hex" )

	def generate_redirect_uri( self ):
		return "{0}://{1}{2}".format(
			self.request.protocol,
			self.request.host,
			self.reverse_url( "auth_github" )
		)

	def get_authenticated_user( self, redirect_uri, client_id, scope, state,
								client_secret=None, code=None,
								success_callback=None,
								error_callback=None ):
		""" Fetches the authenticated user

		:param redirect_uri: the redirect URI
		:param client_id: the client ID
		:param state: the unguessable random string to protect against
					  cross-site request forgery attacks
		:param client_secret: the client secret
		:param code: the response code from the server
		:param success_callback: the success callback used when fetching
								 the access token succeeds
		:param error_callback: the callback used when fetching the access
							   token fails
		"""
		if code:
			self._fetch_access_token(
				code,
				success_callback,
				error_callback,
				scope,
				redirect_uri,
				client_id,
				client_secret,
				state
			)

			return

		params = {
			"redirect_uri": redirect_uri,
			"client_id": client_id,
			"extra_params": {
				"state": state
			}
		}

		self.authorize_redirect( **params )

	def _fetch_access_token( self, code, success_callback, error_callback,
							 scope, redirect_uri, client_id, client_secret, state ):
		""" Fetches the access token.

		:param code: the response code from the server
		:param success_callback: the success callback used when fetching
								 the access token succeeds
		:param error_callback: the callback used when fetching the access
							   token fails
		:param redirect_uri: the redirect URI
		:param client_id: the client ID
		:param client_secret: the client secret
		:param state: the unguessable random string to protect against
					  cross-site request forgery attacks
		:return:
		"""
		if not (client_secret and success_callback and error_callback):
			raise ValueError(
				"The client secret or any callbacks are undefined."
			)

		params = {
			"code": code,
			"redirect_url": redirect_uri,
			"client_id": client_id,
			"client_secret": client_secret,
			"scope": scope,
			"state": state
		}

		http = httpclient.AsyncHTTPClient()

		callback_sharing_data = { }

		def use_error_callback( response, decoded_body ):
			data = {
				"code": response.code,
				"body": decoded_body
			}

			if response.error:
				data["error"] = response.error

			error_callback( **data )

		def decode_response_body( response ):
			""" Decodes the JSON-format response body

			:param response: the response object
			:type response: tornado.httpclient.HTTPResponse

			:return: the decoded data
			"""
			# Fix GitHub response.
			body = codecs.decode( response.body, 'ascii' )
			body = re.sub( '"', '\"', body )
			body = re.sub( "'", '"', body )
			body = json.loads( body )

			if response.error:
				use_error_callback( response, body )

				return None

			return body

		def on_authenticate( response ):
			""" The callback handling the authentication

			:param response: the response object
			:type response: tornado.httpclient.HTTPResponse
			"""
			body = decode_response_body( response )

			if not body:
				return

			if "access_token" not in body:
				use_error_callback( response, body )

				return

			callback_sharing_data["access_token"] = body["access_token"]

			http.fetch(
				"{}{}".format(
					self._OAUTH_USER_URL, callback_sharing_data["access_token"]
				),
				on_fetching_user_information,
				headers=self._API_BASE_HEADERS
			)

		def on_fetching_user_information( response ):
			""" The callback handling the data after fetching the user info

			:param response: the response object
			:type response: tornado.httpclient.HTTPResponse
			"""
			# Fix GitHub response.
			user = decode_response_body( response )

			if not user:
				return

			success_callback( user, callback_sharing_data["access_token"] )

		# Request the access token.
		http.fetch(
			self._OAUTH_ACCESS_TOKEN_URL,
			on_authenticate,
			method="POST",
			body=urlencode( params ),
			headers=self._API_BASE_HEADERS
		)
