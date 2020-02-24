from initiate_database import *
import enum
import json
import uuid
import time
import os

class RefineryUserTier( enum.Enum ):
	# Free tier, makes use of the shared redis cluster
	FREE = 'free'
	# Paid tier, uses their own dedicated redis instance
	PAID = 'paid'

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
	email_verified = Column(
		Boolean(),
		default=False,
	)
	
	# Whether the user's account is disabled
	# A disabled user cannot log in to Refinery
	disabled = Column(
		Boolean(),
		default=False
	)
	
	# If the user has a payment method added
	# This is used to determine if the user's account
	# should be "frozen" after their "free trial" period
	# has expired (e.g. after 14 days or whatever)
	has_valid_payment_method_on_file = Column(
		Boolean(),
		default=False,
	)
	
	# What level the user is in an organization
	# For now there's only one level - ADMIN
	permission_level = Column(
		Text(),
		default="ADMIN",
	)
	
	# Payment ID - currently this means Stripe
	payment_id = Column(Text())
	
	# Phone number of the user
	phone_number = Column(Text())

	# Tier the user's account is under (free/paid)
	tier = Column(
		Enum( RefineryUserTier ),
		default=RefineryUserTier.FREE,
		nullable=False
	)
	
	# Parent organization the user belongs to
	organization_id = Column(
		CHAR(36),
		ForeignKey(
			"organizations.id"
		)
	)
	organization = relationship(
		"Organization",
		back_populates="billing_admin_user"
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
	
	# One user can have many state logs
	state_logs = relationship(
		"StateLog",
		lazy="dynamic",
		# When a user is deleted all session state logs
		# should be deleted as well.
		cascade="all, delete-orphan",
		backref="user",
	)
	
	timestamp = Column(Integer())

	def __init__( self ):
		self.id = str( uuid.uuid4() )
		self.email_verified = False
		self.disabled = False
		self.permission_level = "ADMIN"
		self.has_valid_payment_method_on_file = False
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