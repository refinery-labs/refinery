# coding: utf-8
#
# Copyright (c) Alexandr Emelin. BSD license.
# All rights reserved.
#
# Note: Fairly extensive modifications by Refinery team.
#
from tornado import gen
from tornado.httpclient import HTTPError
from tornado.httputil import url_concat

from controller.auth.github.exceptions import GithubOAuthException
from controller.auth.github.utils import decode_response_body, generate_redirect_uri, generate_state_token
from controller.auth.oauth_user_data import GithubUserData

try:
    from urllib.parse import urlencode
except ImportError:
    # python 3
    # noinspection PyCompatibility, PyUnresolvedReferences
    from urllib.parse import urlencode

from tornado import httpclient


class GithubOAuthProvider:
    """GitHub OAuth2 Authentication

    To authenticate with GitHub, first register your application at
    https://github.com/settings/applications/new to get the client ID and
    secret.

    Docs on the endpoints: https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps/
    """

    _API_BASE_HEADERS = {
        "Accept": "application/json",
        "User-Agent": "Tornado OAuth"
    }
    _OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _OAUTH_USER_URL = "https://api.github.com/user?access_token="

    # Since we only need email address
    scope = "user:email"

    def __init__(self, app_config, logger):

        client_id = app_config.get("github_client_id"),
        client_secret = app_config.get("github_client_secret"),
        cookie_expire_days = app_config.get("cookie_expire_days"),

        if client_id is None or client_secret is None:
            raise Exception("Missing client credentials for Github OAuth API")

        if cookie_expire_days is None:
            raise Exception("Missing cookie configuration for Github OAuth client")

        self.client_id = client_id
        self.client_secret = client_secret
        self.cookie_expire_days = cookie_expire_days
        self.logger = logger

        # TODO: Allow this to be stubbed via the constructor
        self.http = httpclient.AsyncHTTPClient()

    def redirect_user_to_login(self, ctx):
        """
        This is the first leg of the OAuth flow.
        We setup the state for the user and send them the URI for Github to approve the access request.
        :param ctx: This is the "self" of a Tornado request controller.
        """
        state = generate_state_token()

        redirect_uri = generate_redirect_uri(ctx)

        # Set authentication cookie
        ctx.set_secure_cookie(
            "github_oauth_state",
            state,
            expires_days=int(self.cookie_expire_days)
        )

        params = {
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "state": state,
            "response_type": "code"
        }

        # Send back the URL for the client to redirect to.
        ctx.write({
            "success": True,
            "result": {
                "redirect_uri": url_concat(self._OAUTH_AUTHORIZE_URL, params)
            }
        })

    @gen.coroutine
    def retrieve_user_via_oauth_code(self, code, client_state):
        """
        Second leg of the OAuth flow.
        Fetches the user data from Github and returns an OAuthUserData instance with the data.
        :rtype: OAuthUserData Instance of the user data holder object.
        :exception GithubOAuthException: Thrown when an invalid OAuth flow step occurs (data inconsistent, etc)
        """

        # Exchange the temporary code for a long-lived OAuth access_token
        access_token = yield self._fetch_access_token(code, client_state)

        user_data_response = yield self._fetch_user_via_access_token(access_token)

        user_unique_id = user_data_response["id"]
        user_email = user_data_response["email"]
        user_name = user_data_response["name"]

        self.logger("Successfully retrieved data for user from Github for user: " + user_email, "info")

        raise gen.Return(GithubUserData(user_unique_id, user_email, user_name, access_token, user_data_response))

    @gen.coroutine
    def _fetch_access_token(self, code, state):
        """ Second leg of the OAuth flow. Fetches the access token.

        :param code: the response code from the server
        :param state: the unguessable random string to protect against cross-site request forgery (CSRF) attacks
        :return: An dict containing a success field indicating status. Other properties are relevant data.
        """

        #redirect_uri = generate_redirect_uri( ctx )

        params = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
            "state": state
        }

        try:
            # Request the access token.
            response = yield self.http.fetch(
                self._OAUTH_ACCESS_TOKEN_URL,
                method="POST",
                body=urlencode(params),
                headers=self._API_BASE_HEADERS
            )
        except HTTPError as e:
            raise self._trigger_oauth_exception("Github authentication exception", data=e)

        body = decode_response_body(response)

        self.logger("Response received: " + repr(body))

        if not body:
            raise self._trigger_oauth_exception("Missing body from Github response", data=response)

        if "error" in body:
            raise self._trigger_oauth_exception("Github authentication error", data=response)

        # Validate that the shape of the data matches what we expect
        if "access_token" not in body:
            raise self._trigger_oauth_exception("Missing access token from Github response", data=response)

        access_token = body["access_token"]

        raise gen.Return(access_token)

    @gen.coroutine
    def _fetch_user_via_access_token(self, access_token):
        """
        The callback handling the data after fetching the user info
        :param access_token: The access token returned by Github during the second part of the flow.
        """
        try:
            response = yield self.http.fetch(
                "{}{}".format(
                    self._OAUTH_USER_URL,
                    access_token
                ),
                headers=self._API_BASE_HEADERS
            )
        except HTTPError as e:
            raise self._trigger_oauth_exception("Unable to retrieve user information via token from Github", data=e)

        # Fix GitHub response.
        user = decode_response_body(response)

        self.logger("Response received: " + repr(user))

        if not user:
            raise self._trigger_oauth_exception("Missing body when retrieving user information via token from Github")

        # if "email" not in user or "name" not in user[ "user" ]:
        #	raise self._trigger_oauth_exception( "Invalid response from Github -- missing required data", data=response )

        # Hand back the user object for future usage
        raise gen.Return(user)

    def _trigger_oauth_exception(self, message, data=None, level="warning"):
        """
        Returns a value for a co-routine indicating failure.
        :param message: Message to be logged and placed into the output dict.
        :param data: Optional data to print in the log message.
        :param level: Optional log level to emit.
        :return: A dictionary with "success" set as false and "message" set as a string.
        """
        if data is not None:
            self.logger(message + ": " + repr(data), level)
        else:
            self.logger(message, level)

        return GithubOAuthException(message)
