import os

import tornado
from tornado import gen

from controller.auth.github_auth_mixin import GithubMixin
from utils.general import logit


class AuthenticateWithGithub( GithubMixin ):
	# Since we only need email address
	scope = "user:email"

	@gen.coroutine
	def get( self ):
		client_id = os.environ["github_client_id"]
		client_secret = os.environ["github_client_secret"]

		code = self.get_argument( "code", None )

		# Check that the request is valid
		if code is None:
			self.respond_with_error( "Missing OAuth response code" )
			return

		session_data = self.get_secure_cookie_data( "github_oauth_state", 1 )

		if session_data is None:
			self.respond_with_error( "Missing cookie session data" )
			return

		client_state = self.get_argument( "state", None )

		if client_state is None:
			self.respond_with_error( "Missing state token in parameters" )
			return

		if client_state != session_data:
			self.respond_with_error( "Client state and session state mismatched" )
			return

		# For security reason, the state value (cross-site token) will be
		# retrieved from the query string.
		params = {
			"redirect_uri": self.generate_redirect_uri(),
			"client_id": client_id,
			"client_secret": client_secret,
			"success_callback": self._on_auth,
			"error_callback": self._on_error,
			"scope": self.scope,
			"code": code,
			"state": client_state
		}
		self.get_authenticated_user( **params )
		return

	@gen.coroutine
	def post( self ):
		client_id = os.environ["github_client_id"]

		state_token = self.generate_state_token()

		params = {
			"redirect_uri": self.generate_redirect_uri(),
			"client_id": client_id,
			"scope": self.scope,
			"state": state_token
		}

		# Set authentication cookie
		self.set_secure_cookie(
			"github_oauth_state",
			state_token,
			expires_days=int( os.environ.get( "cookie_expire_days" ) )
		)

		# Redirect for user authentication
		self.get_authenticated_user( **params )

	def respond_with_error( self, msg ):
		logit( "Github oauth error: " + msg, "warning" )
		self.set_status( 400 )
		self.write( {
			"success": False,
			"msg": "Invalid state for flow"
		} )

	@gen.coroutine
	def _on_auth( self, user, access_token=None ):
		if not user:
			raise tornado.web.HTTPError( 500, "Github auth failed" )
		# user_data, error = yield storage.get_or_create_user(
		#	self.db,
		#	user['email']
		# )
		# if error:
		#	raise tornado.web.HTTPError(500, "Auth failed")
		# self.set_secure_cookie("user", tornado.escape.json_encode(user_data))
		print('user logged in now: ' + repr( user ))

		# TODO: Make this redirect properly
		# self.redirect("/")

	def _on_error( self, code, body=None, error=None ):
		if body:
			logit( "Github login issue: " + repr( body ), "error" )
		if error:
			logit( "Github login error: " + repr( error ), "error" )
		raise tornado.web.HTTPError( 500, "Github auth failed" )
