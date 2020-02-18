from initiate_database import *
import json
import uuid
import time
import os

class LambdaExecutions( Base ):
	"""
	This receives WebHook HTTP requests from the Lambda 
	(ProcessIncomingLambdaExecutionMetadata) which is hooked
	up to a Kinesis stream that automatically receives the
	executed Lambda details in near real-time. These execution
	details contain information like memory allocated,
	execution time in milliseconds, billed time in milliseconds
	etc.

	Using this data we can calculate free-tier user usage in 
	near real-time and limit accounts hitting their ceiling
	almost instantly.
	"""
	__tablename__ = "lambda_executions"

	id = Column(CHAR(36), primary_key=True)
	
	# The AWS account ID
	account_id = Column(
		Text(),
		ForeignKey(
			"aws_accounts.account_id"
		),
		index=True,
	)

	# The Cloudwatch Log name
	log_name = Column(
		Text()
	)

	# The Cloudwatch Log stream
	log_stream = Column(
		Text()
	)

	# The name of the Lambda
	lambda_name = Column(
		Text()
	)

	# The raw log line, might be useful
	# at a later time
	raw_line = Column(
		Text()
	)

	# The timestamp when the execution
	# happened in seconds.
	execution_timestamp = Column(
		BigInteger()
	)

	# The timestamp when the execution
	# happened in milliseconds.
	execution_timestamp_ms = Column(
		BigInteger()
	)

	# The *actual* duration of the
	# Lambda execution in milliseconds
	duration = Column(
		Float()
	)

	# Duration in milliseconds that the
	# Lambda ended up being billed at.
	billed_duration = Column(
		BigInteger()
	)

	# Memory size in MB of the Lambda
	memory_size = Column(
		BigInteger()
	)

	# The max memory size in MB used
	# by the Lambda.
	max_memory_used = Column(
		BigInteger()
	)

	# The unique report request ID for
	# this particular log line (UUID)
	report_requestid = Column(
		Text()
	)

	# Time of insert
	timestamp = Column(
		Integer(),
		index=True
	)

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"account_id",
			"log_name",
			"log_stream",
			"lambda_name",
			"raw_line",
			"timestamp",
			"execution_timestamp",
			"execution_timestamp_ms",
			"duration",
			"memory_size",
			"max_memory_used",
			"billed_duration",
			"report_requestid",
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