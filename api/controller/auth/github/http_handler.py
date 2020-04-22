import os
import pinject
from tornado import gen

from assistants.user_creation_assistant import UserCreationAssistant
from controller.base import BaseHandler
from controller.auth.github.exceptions import GithubOAuthException, BadRequestStateException
from controller.auth.github.oauth_provider import GithubOAuthProvider

# Example data returned by Github
# {
#   "public_repos": 57,
#   "site_admin": false,
#   "subscriptions_url": "https://api.github.com/users/freeqaz/subscriptions",
#   "gravatar_id": "",
#   "hireable": None,
#   "id": 4573221,
#   "followers_url": "https://api.github.com/users/freeqaz/followers",
#   "following_url": "https://api.github.com/users/freeqaz/following{/other_user}",
#   "blog": "http://freeqaz.com/",
#   "followers": 35,
#   "location": "Seattle, WA",
#   "type": "User",
#   "email": "jw@freeqaz.com",
#   "bio": "Security and software professional with a knack for building MMO video games.",
#   "gists_url": "https://api.github.com/users/freeqaz/gists{/gist_id}",
#   "company": None,
#   "events_url": "https://api.github.com/users/freeqaz/events{/privacy}",
#   "html_url": "https://github.com/freeqaz",
#   "updated_at": "2020-02-10T22:28:03Z",
#   "node_id": "MDQ6VXNlcjQ1NzMyMjE=",
#   "received_events_url": "https://api.github.com/users/freeqaz/received_events",
#   "starred_url": "https://api.github.com/users/freeqaz/starred{/owner}{/repo}",
#   "public_gists": 3,
#   "name": "Johnathan Free Wortley",
#   "organizations_url": "https://api.github.com/users/freeqaz/orgs",
#   "url": "https://api.github.com/users/freeqaz",
#   "created_at": "2013-05-30T18:18:38Z",
#   "avatar_url": "https://avatars1.githubusercontent.com/u/4573221?v=4",
#   "repos_url": "https://api.github.com/users/freeqaz/repos",
#   "following": 24,
#   "login": "freeqaz"
# }
from controller.decorators import authenticated


class AuthenticateWithGithubDependencies:
	@pinject.copy_args_to_public_fields
	def __init__(self, github_oauth_provider, user_creation_assistant):
		"""
		Called by Tornado with dependencies for this service to run.
		:param github_oauth_provider: Instance of GithubOAuthProvider
		:type github_oauth_provider: GithubOAuthProvider
		:param user_creation_assistant: Instance of UserCreationAssistant
		:type user_creation_assistant: UserCreationAssistant
		"""
		pass


# noinspection PyMethodOverriding, PyAttributeOutsideInit
class AuthenticateWithGithub( BaseHandler ):
	dependencies = AuthenticateWithGithubDependencies
	github_oauth_provider = None  # type: GithubOAuthProvider
	user_creation_assistant = None  # type: UserCreationAssistant

	@gen.coroutine
	def get( self ):
		# TODO: Add JSON Schema validation here

		try:
			code, client_state = self.retrieve_and_validate_request_data()

			oauth_user_data = yield self.github_oauth_provider.retrieve_user_via_oauth_code( code, client_state )

			# Opens the database session (explicitly)
			# TODO: Replace this via a "with" statement once we have that setup
			dbsession = self.dbsession

			user = self.get_authenticated_user()
			# case 1: user is already logged in and we simply associate the user with the oauth data
			if not user:
				# case 2: user is not logged in, but they already have an existing Refinery account
				# case 3: user is not logged in, and they do not have a Refinery account.
				user = yield self.user_creation_assistant.find_or_create_user_via_oauth( dbsession, oauth_user_data, self.request )

			# This writes the OAuth token to the database
			self.user_creation_assistant.update_user_oauth_record(
				dbsession,
				user,
				oauth_user_data
			)

			dbsession.commit()

			# Log the user in :)
			self.authenticate_user_id( user.id )

		except BadRequestStateException as e:
			self.respond_with_error( e.message )
			raise gen.Return()
		except GithubOAuthException as e:
			self.respond_with_error( e.message )
			raise gen.Return()

		# return script for closing this window, the user should be taken back to the original page
		# they started the oauth flow from
		nonce = str(os.urandom(16)).encode("base64").replace('\n', '')

		self.set_header("Content-Security-Policy", "script-src 'nonce-{nonce}'".format(nonce=nonce))
		self.write("<html><script nonce=\"{nonce}\">window.close();</script></html>".format(nonce=nonce))

	@gen.coroutine
	def post( self ):
		"""
		This endpoint initiates the Github Authentication OAuth flow.
		Does not require any parameters. It is a POST request to avoid CSRF attacks (CSRF validation in BaseHandler).
		"""
		# Handles writing to the request both the state cookie and response JSON with URI for the redirect flow.
		self.github_oauth_provider.redirect_user_to_login( self )

	def respond_with_error( self, msg ):
		self.logger( "Github oauth error: " + msg, "warning" )
		self.set_status( 400 )
		self.write({
			"success": False,
			"result": {
				"msg": "Invalid state for Github flow"
			}
		})
		return BadRequestStateException( msg )

	def retrieve_and_validate_request_data( self ):
		"""
		Reads the Tornado session and validates if the OAuth session is valid.
		:return: (code, client_state): First is the OAuth code, Second is the client OAuth state
		"""

		# Parse out any arguments and validate them
		code = self.get_argument( "code", None )

		if code is None:
			raise BadRequestStateException( "Missing OAuth response code" )

		# Grab "first copy" of our OAuth state token
		oauth_state_cookie = self.get_secure_cookie_data( "github_oauth_state", 1 )

		if oauth_state_cookie is None:
			raise BadRequestStateException( "Missing cookie session data" )

		# Grab "second copy" of our OAuth state token
		client_state = self.get_argument( "state", None )

		if client_state is None:
			raise BadRequestStateException( "Missing state token in parameters" )

		# Compares tokens to validate the request originated from the same user (is not a CSRF attack)
		if client_state != oauth_state_cookie:
			raise BadRequestStateException( "Client state and session state mismatched" )

		return code, client_state
