import json
import uuid
import time

from sqlalchemy import Column, CHAR, Text, ForeignKey, BigInteger, Float, Integer

from models.initiate_database import Base


class LambdaExecutionMonthlyReport(Base):
	__tablename__ = "lambda_execution_monthly_reports"

	id = Column(CHAR(36), primary_key=True)

	# The AWS account ID
	account_id = Column(
		Text(),
		ForeignKey(
			"aws_accounts.account_id"
		),
		index=True,
	)

	gb_seconds_used = Column(
		Float()
	)

	total_executions = Column(
		Integer()
	)

	# Time of insert
	timestamp = Column(
		Integer(),
		index=True
	)

	def __init__(self, account_id, gb_seconds_used):
		self.id = str( uuid.uuid4() )
		self.account_id = account_id
		self.gb_seconds_used = gb_seconds_used
		self.total_executions = 0
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"account_id",
			"gb_seconds_used",
			"total_executions",
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