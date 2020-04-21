import pinject

from controller.auth.oauth_user_data import OAuthUserData
from models.user_oauth_account import UserOAuthAccountModel
from models.user_oauth_data_record import UserOAuthDataRecordModel
from models.users import User


class OAuthServiceBindingSpec(pinject.BindingSpec):
	@pinject.provides("oauth_service")
	def provider_oauth_service( self, logger ):
		return OAuthService(logger)


class OAuthService:

	def __init__( self, logger ):
		"""
		Manages creation of OAuth records in the database via SQLAlchemy.
		:type logger: logit
		"""
		self.logger = logger

	def add_token_for_user( self, dbsession, user, oauth_user_data ):
		"""
		Associates the OAuth data against an existing user.
		:type dbsession: sqlalchemy.orm.Session
		:param user: User to associate the OAuth data with.
		:type user: User
		:param oauth_user_data: OAuth record to associate with the user.
		:type oauth_user_data: OAuthUserData
		:returns The OAuth account record for the provider
		:rtype UserOAuthAccountModel
		"""

		user_oauth_account = self.create_or_retrieve_existing_oauth_provider_for_user(
			dbsession,
			oauth_user_data.provider_unique_id,
			user.id,
			oauth_user_data.provider
		)

		print user_oauth_account

		user_oauth_data_record = UserOAuthDataRecordModel(
			oauth_user_data.raw_response_data,
			oauth_user_data.access_token,
			user_oauth_account.id
		)

		user_oauth_account.oauth_data_records.append( user_oauth_data_record )

		user.oauth_token_entries.append( user_oauth_account )

		return user_oauth_account

	def create_or_retrieve_existing_oauth_provider_for_user( self, dbsession, provider_unique_id, user_id, provider ):
		"""
		Locates and returns an OAuth provider record for a given user_id and provider type.
		If none exists, it will create a new OAuth record instance.
		:type dbsession: sqlalchemy.orm.Session
		:param provider_unique_id: Unique ID for user, as provided by the OAuth provider.
		:type provider_unique_id: basestring
		:param user_id: ID of a user
		:type user_id: basestring
		:param provider: The provider type
		:type provider: basestring
		:return: A matching record or nothing.
		:rtype UserOAuthAccountModel
		"""

		user_oauth_account = self.get_existing_oauth_provider_for_user( dbsession, user_id, provider )

		if user_oauth_account is not None:
			return user_oauth_account

		# Create a new record if one doesn't exist
		return UserOAuthAccountModel( provider, provider_unique_id, user_id )

	def get_existing_oauth_provider_for_user( self, dbsession, user_id, provider ):
		"""
		Locates and returns an OAuth provider record for a given user_id and provider type.
		:type dbsession: sqlalchemy.orm.Session
		:param user_id: ID of a user
		:type user_id: basestring
		:param provider: The provider type
		:type provider: basestring
		:return: A matching record or nothing.
		:rtype Optional[UserOAuthAccountModel]
		"""
		return dbsession.query( UserOAuthAccountModel ).filter(
			UserOAuthAccountModel.user_id == user_id,
			UserOAuthAccountModel.provider == provider
		).first()
