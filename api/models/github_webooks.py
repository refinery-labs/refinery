import binascii

from data_types.oauth_providers import OAuthProvider
from sqlalchemy import Enum, Index, TEXT
from initiate_database import *
import json
import uuid

from models.model_exceptions import InvalidModelCreationError
from models.projects import Project


class GithubWebhook( Base ):
	"""
	"""
	__tablename__ = "github_webhooks"

	id = Column(
		TEXT(),
		primary_key=True
	)

	webhook_id = Column(
		Integer()
	)

	secret = Column(
		TEXT()
	)

	project_id = Column(
		CHAR(36),
		ForeignKey( Project.id ),
	)

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.secret = binascii.hexlify(
			os.urandom(32)
		)
