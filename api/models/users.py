from initiate_database import *
import json
import uuid
import time
import os

class User( Base ):
	__tablename__ = "users"
	
	id = Column(
		CHAR(36),
		primary_key=True
	)
	
	# The name of the user
	name = Column(Text())
	
	# Email address of the user
	# Unique constraint because users should only sign up
	# with one email address per account.
	email = Column(
		Text(),
		unique=True
	)
	
	# Whether we've validated ownership of the email
	email_verified = Column(Boolean())
	
	# Whether the user's account is disabled
	disabled = Column(Boolean())
	
	# What level the user is in an organization
	# For now there's only one level - ADMIN
	permission_level = Column(Text())
	
	# Parent organization the user belongs to
	organization_id = Column(
		CHAR(36),
		ForeignKey(
			"organizations.id"
		)
	)
	
	# Many to many relationship to users
	# A user can belong to many projects
	# A project can belong to many users
	projects = relationship(
		"Project",
		lazy="dynamic",
		secondary=users_projects_association_table,
		back_populates="users"
	)
	
	# One user can have many email auth tokens
	# When a user is deleted it makes sense to clear all
	# auth tokens from the database
	email_auth_tokens = relationship(
		"EmailAuthToken",
		lazy="dynamic",
		# When a user is deleted all auth tokens should
		# be deleted as well.
		cascade="all, delete-orphan",
		backref="user",
	)
	
	# One user can have many saved functions
	# When a user is deleted it makes sense to clear all
	# saved functions from the database as well.
	saved_functions = relationship(
		"SavedFunction",
		lazy="dynamic",
		# When a user is deleted all saved functions should
		# be deleted as well.
		cascade="all, delete-orphan"
	)
	
	timestamp = Column(Integer())

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.email_verified = False
		self.disabled = False
		self.permission_level = "ADMIN"
		self.timestamp = int( time.time() )

	def to_dict( self ):
		exposed_attributes = [
			"id",
			"name",
			"email",
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