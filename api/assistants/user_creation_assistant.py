import pinject
from tornado import gen

from models.organizations import Organization
from models.users import User


class UserCreationAssistant:
	@pinject.copy_args_to_public_fields
	def __init__(
			self,
			logger,
			oauth_service,
			github_oauth_provider,
			project_inventory_service,
			stripe_service,
			user_management_service
	):
		"""
		This class contains logic for creating and managing User instances by utilizing many services.
		:type logger: logit
		:type oauth_service: OAuthService
		:type github_oauth_provider: GithubOAuthProvider
		:type project_inventory_service: ProductInventoryService
		:type stripe_service: StripeService
		:type user_service: UserService
		"""
		pass

	@gen.coroutine
	def setup_initial_user_state( self, dbsession, request, user ):
		"""
		Handles setting up the initial state for a new user.
		Should be called whenever a new user is created (sets up example projects, etc).
		:type dbsession: sqlalchemy.orm.Session
		:param request: Subset of the Tornado request object to pull headers from.
		:type user: User
		"""
		customer_id = yield self.create_stripe_record_for_user( request, user )
		user.payment_id = customer_id

		example_projects = self.project_inventory_service.add_example_projects_user( user )

		for project in example_projects:
			dbsession.add( project )

	def login_user_via_oauth( self, dbsession, oauth_user_data ):
		"""
		Logs a user into Refinery via OAuth.
		:type dbsession: sqlalchemy.orm.Session
		:param oauth_user_data: Instance of OAuthUserData that contains information to process the OAuth login.
		:type oauth_user_data: OAuthUserData
		:return: User that was located and updated
		"""

		self.logger( "Searching database for user: " + repr( oauth_user_data.email ) )
		user = self.oauth_service.search_for_existing_user(
			dbsession,
			oauth_user_data
		)

		# Just update the user and log them in
		if user is None:
			return None

		# This records the latest OAuth token to the database
		self.update_user_oauth_record(
			dbsession,
			user,
			oauth_user_data
		)

		# Save the state to the database
		dbsession.add( user )

		self.logger( "Successful Github OAuth login flow for user: " + repr( user.email ) )

		return user

	@gen.coroutine
	def create_new_user_via_oauth( self, dbsession, request, oauth_user_data ):
		"""
		Creates a user via OAuth.
		:type dbsession: sqlalchemy.orm.Session
		:param request: Subset of the Tornado request object to pull headers from.
		:param oauth_user_data: Instance of OAuthUserData that contains information to process the OAuth login.
		:type oauth_user_data: OAuthUserData
		:return: New user that was created
		"""
		user, organization = self.user_service.create_new_user_and_organization(
			dbsession,
			oauth_user_data.name,
			oauth_user_data.email,
			require_email_verification=False
		)

		# This writes the OAuth token to the database
		self.update_user_oauth_record(
			dbsession,
			user,
			oauth_user_data
		)

		yield self.setup_initial_user_state( dbsession, request, user )

		# This adds all of the different "relationships" of data in one step (organization, user, oauth, oauth data)
		dbsession.add( organization )

		self.logger( "Wrote new user to the database: " + user.email )

		raise gen.Return( user )

	def update_user_oauth_record( self, dbsession, user, oauth_user_data ):
		"""
		Creates a user via OAuth.
		:type dbsession: sqlalchemy.orm.Session
		:param user: User instance to add OAuth record to
		:type user: User
		:param oauth_user_data: Instance of OAuthUserData that contains information to process the OAuth login.
		:type oauth_user_data: OAuthUserData
		"""
		user_oauth_account = self.oauth_service.add_token_for_user(
			dbsession,
			user,
			oauth_user_data
		)

		user.oauth_token_entries.append( user_oauth_account )

	@gen.coroutine
	def create_stripe_record_for_user( self, request, user ):

		# Stash some information about the signup in case we need it later
		# for fraud-style investigations.
		user_agent = request.headers.get( "User-Agent", "Unknown" )
		x_forwarded_for = request.headers.get( "X-Forwarded-For", "Unknown" )
		client_ip = request.remote_ip

		customer_id = yield self.stripe_service.create_new_customer(
			user,
			user_agent,
			x_forwarded_for,
			client_ip
		)

		raise gen.Return( customer_id )
