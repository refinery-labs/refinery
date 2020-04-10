import boto3
import pinject
from botocore.client import Config


class AWSClientBindingSpec(pinject.BindingSpec):
	def configure( self, bind ):
		pass

	@pinject.provides('aws_cost_explorer')
	def new_aws_cost_explorer(self, app_config):
		# This is another global Boto3 client because we need root access
		# to pull the billing for all of our sub-accounts
		return boto3.client(
			"ce",
			aws_access_key_id=app_config.get( "aws_access_key" ),
			aws_secret_access_key=app_config.get( "aws_secret_key" ),
			region_name=app_config.get( "region_name" ),
			config=Config(
				max_pool_connections=( 1000 * 2 )
			)
		)

	@pinject.provides('aws_organization_client')
	def new_aws_organization_client(self, app_config):
		# The AWS organization API for provisioning new AWS sub-accounts
		# for customers to use.
		return boto3.client(
			"organizations",
			aws_access_key_id=app_config.get( "aws_access_key" ),
			aws_secret_access_key=app_config.get( "aws_secret_key" ),
			region_name=app_config.get( "region_name" ),
			config=Config(
				max_pool_connections=( 1000 * 2 )
			)
		)

	@pinject.provides('aws_lambda_client')
	def new_aws_lambda_client( self, app_config ):
		"""
		This client is used to emit metrics and logs by other classes on the server.
		:param app_config: App Config instance to pull config from
		:return: Shared instance of the Cloudwatch client
		"""
		return boto3.client(
			"lambda",
			aws_access_key_id=app_config.get( "aws_access_key" ),
			aws_secret_access_key=app_config.get( "aws_secret_key" ),
			region_name=app_config.get( "region_name" ),
			config=Config(
				max_pool_connections=( 1000 * 2 )
			)
		)

	@pinject.provides('aws_cloudwatch_client')
	def new_aws_cloudwatch_client( self, app_config ):
		"""
		This client is used to emit metrics and logs by other classes on the server.
		:param app_config: App Config instance to pull config from
		:return: Shared instance of the Cloudwatch client
		"""
		return boto3.client(
			"cloudwatch",
			aws_access_key_id=app_config.get( "aws_access_key" ),
			aws_secret_access_key=app_config.get( "aws_secret_key" ),
			region_name=app_config.get( "region_name" )
		)
