from initiate_database import *
import json
import uuid
import time
import os

class GitRepo( Base ):
	__tablename__ = "git_repos"

	id = Column(Text(), primary_key=True)

	# Parent user the saved function
	project_id = Column(
		CHAR(36),
		ForeignKey(
			"projects.id"
		)
	)

	url = Column(Text())

	blocks = relationship(
		"SavedBlock",
		backref="git_repos",
		cascade="all, delete-orphan"
	)

	def __init__( self, project_id, url ):
		self.id = str( uuid.uuid4() )
		self.project_id = project_id
		self.url = url

	def __str__( self ):
		return self.id
