from initiate_database import *
import json
import uuid
import time
import os

class AWSAccount( Base ):
	__tablename__ = "aws_accounts"

	id = Column(
		CHAR(36),
		primary_key=True
	)
	
	# Label for the AWS account
	# Leave blank for now until we support multiple
	# AWS accounts.
	account_label = Column(Text())
	
	# AWS account ID
	account_id = Column(Text())
	
	# AWS region
	region = Column(Text())
	
	# S3 bucket suffix, used to generate the full
	# bucket names for sub-accounts
	s3_bucket_suffix = Column(Text())
	
	# AWS IAM Console Admin username
	iam_admin_username = Column(Text())
	
	# AWS IAM Console Admin password
	iam_admin_password = Column(Text())
	
	# Redis hostname
	redis_hostname = Column(Text())
	
	# Redis password
	redis_password = Column(Text())
	
	# Redis port
	redis_port = Column(BigInteger())
	
	# Redis secret prefix
	redis_secret_prefix = Column(Text())
	
	# The AWS account type, which can be any of the following:
	# MANAGED || UNMANAGED
	# MANAGED is for sub-accounts that we manage
	# UNMANAGED is for third-party AWS accounts we don't manage.
	account_type = Column(Text())
	
	# Whether the AWS Account is a "reserved account"
	# Reserved accounts are sub-accounts of the main Refinery
	# account. They are allocated to new users in order to do
	# reseller pricing of AWS usage.
	is_reserved_account = Column(Boolean())
	
	timestamp = Column(Integer())
	
	# Parent organization the AWS account belongs to
	organization_id = Column(
		CHAR(36),
		ForeignKey(
			"organizations.id"
		)
	)
	
	# Deployments this AWS account is associated with
	deployments = relationship(
		"Deployment",
		lazy="dynamic"
	)
	
	# The cached billing collections for this AWS account
	cached_billing_collections = relationship(
		"CachedBillingCollection",
		back_populates="aws_account",
		lazy="dynamic"
	)
	
	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.is_reserved_account = False
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"account_id",
			"region",
			"s3_bucket_suffix",
			"iam_admin_username",
			"iam_admin_password",
			"redis_hostname",
			"redis_password",
			"redis_port",
			"account_type",
			"is_reserved_account",
			"timestamp"
		]
		
		json_attributes = []
		return_dict = {}

		for attribute in exposed_attributes:
			if attribute in json_attributes:
				return_dict[ attribute ] = json.loads(
					getattr( self, attribute )
				)
			else:
				return_dict[ attribute ] = getattr( self, attribute )
				
		# Generate S3 packages and logging bucket values
		return_dict[ "lambda_packages_bucket" ] = "refinery-lambda-build-packages-" + self.s3_bucket_suffix
		return_dict[ "logs_bucket" ] = "refinery-lambda-logging-" + self.s3_bucket_suffix

		return return_dict

	def __str__( self ):
		return self.id