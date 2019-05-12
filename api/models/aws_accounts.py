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
	account_label = Column(Text())
	
	# AWS account ID
	account_id = Column(BigInteger())
	
	# AWS access key
	access_key = Column(Text())
	
	# AWS secret key
	secret_key = Column(Text())
	
	# AWS region
	region = Column(Text())
	
	# Lambda packages S3 bucket
	lambda_packages_bucket = Column(Text())
	
	# Logs S3 bucket
	logs_bucket = Column(Text())
	
	# AWS IAM Console Admin username
	iam_admin_username = Column(Text())
	
	# AWS IAM Console Admin password
	iam_admin_password = Column(Text())
	
	# Whether the AWS Account is a "reserved account"
	# Reserved accounts are sub-accounts of the main Refinery
	# account. They are allocated to new users in order to do
	# reseller pricing of AWS serverless usage.
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
	
	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.is_reserved_account = False
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"account_id",
			"access_key",
			"secret_key",
			"region",
			"lambda_packages_bucket",
			"logs_bucket",
			"iam_admin_username",
			"iam_admin_password",
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

		return return_dict

	def __str__( self ):
		return self.id