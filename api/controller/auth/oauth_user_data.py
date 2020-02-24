from controller.auth.github.exceptions import InvalidOAuthDataException


class OAuthUserData:
	def __init__( self, provider, provider_unique_id, email, name, access_token, raw_response_data ):
		if provider is None or provider is "":
			raise InvalidOAuthDataException( "Invalid provider for OAuth user data" )

		if email is None or name is None or access_token is None or raw_response_data is None:
			raise InvalidOAuthDataException( "Invalid parameter for OAuth user data" )

		self.provider = provider
		# Cast this to a string because we store this is as a string on our side.
		self.provider_unique_id = str( provider_unique_id )
		self.email = email
		self.name = name
		self.access_token = access_token
		self.raw_response_data = raw_response_data


class GithubUserData(OAuthUserData):
	def __init__( self, provider_unique_id, email, name, access_token, raw_response_data ):
		OAuthUserData.__init__( self, "github", provider_unique_id, email, name, access_token, raw_response_data )

