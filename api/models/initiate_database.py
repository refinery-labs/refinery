import yaml
import os

from sqlalchemy import create_engine
engine = create_engine( "postgresql://" + os.environ.get( "postgreql_username" ) + ":" + os.environ.get( "postgreql_password" ) + "@" + os.environ.get( "postgresql_host" ) + "/" + os.environ.get( "postgres_db" ) + "?client_encoding=utf8", pool_recycle=60, encoding="utf8")
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import or_ as sql_or
from sqlalchemy import Column, Integer, String, func, update, Text, Binary, Boolean, BigInteger, event, select, exc, CHAR, ForeignKey, JSON, Table, Float, Enum
from sqlalchemy.orm import sessionmaker, scoped_session, relationship, synonym
from contextlib import contextmanager

DBSession = scoped_session(sessionmaker(
	bind=engine,
	autocommit=False,
	autoflush=True
))

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