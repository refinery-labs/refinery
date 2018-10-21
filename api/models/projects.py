from initiate_database import *
import json
import uuid
import time
import os

class Project( Base ):
    __tablename__ = "projects"

    id = Column(CHAR(36), primary_key=True)
    name = Column(
    	Text(),
    	unique=True
    )
    versions = relationship(
    	"ProjectVersion",
    	backref="projects",
		lazy="dynamic",
		cascade="all, delete-orphan"
	)
    timestamp = Column(Integer())

    def __init__( self ):
        self.id = str( uuid.uuid4() )
        self.timestamp = int( time.time() )

    def to_dict( self ):
        exposed_attributes = [
        	"id",
        	"name",
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