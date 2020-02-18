import yaml
import os

from sqlalchemy import create_engine

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import or_ as sql_or
from sqlalchemy import Column, Integer, String, func, update, Text, Binary, Boolean, BigInteger, event, select, exc, CHAR, ForeignKey, JSON, Table
from sqlalchemy.orm import sessionmaker, scoped_session, relationship, synonym
from contextlib import contextmanager

if "SKIP_DATABASE_CONNECT" not in os.environ:
	# TODO: Don't initiate the database connection on import -- likely move into an exported function
	engine = create_engine( "postgresql://" + os.environ.get( "postgreql_username" ) + ":" + os.environ.get( "postgreql_password" ) + "@" + os.environ.get( "postgresql_host" ) + "/" + os.environ.get( "postgres_db" ) + "?client_encoding=utf8", pool_recycle=60, encoding="utf8")

	# TODO: Generate this lazily to allow for testing (don't call on import)
	DBSession = scoped_session(sessionmaker(
		bind=engine,
		autocommit=False,
		autoflush=True
	))

# TODO: Move this into another file
users_projects_association_table = Table(
	"user_projects_association",
	Base.metadata,
	Column(
		"users",
		CHAR(36),
		ForeignKey(
			"users.id"
		)
	),
	Column(
		"projects",
		CHAR(36),
		ForeignKey(
			"projects.id"
		)
	)
)
