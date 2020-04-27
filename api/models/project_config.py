from initiate_database import *
from projects import Project
import json
import uuid
import time


class ProjectConfig( Base ):
	"""
	A project config holds all of the state related to a given project.
	
	This includes environment variables, API Gateway deployment IDs, etc.
	"""
	__tablename__ = "project_configs"
	
	id = Column(CHAR(36), primary_key=True)
	project_id = Column(
		CHAR(36),
		ForeignKey( Project.id ),
		primary_key=True
	)
	config_json = Column(Text())
	timestamp = Column(Integer())

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"project_id",
			"config_json",
			"timestamp"
		]
		
		json_attributes = [ "config_json" ]
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
