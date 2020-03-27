import boto3
from botocore.client import Config


def new_aws_cost_explorer(app_config):
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


def new_aws_organization_client(app_config):
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
