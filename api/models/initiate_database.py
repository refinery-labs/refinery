import pinject
import yaml
import os

from sqlalchemy import create_engine

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import or_ as sql_or
from sqlalchemy import Column, Integer, String, func, update, Text, Binary, Boolean, BigInteger, event, select, exc, CHAR, ForeignKey, JSON, Table, DateTime, LargeBinary
from sqlalchemy.orm import sessionmaker, scoped_session, relationship, synonym
from contextlib import contextmanager

engine_url_format = "postgresql://{username}:{password}@{host}/{db}?client_encoding=utf8"


def get_refinery_engine( app_config ):
	postgresql_username = app_config.get( "postgreql_username" )
	postgresql_password = app_config.get( "postgreql_password" )
	postgresql_host = app_config.get( "postgresql_host" )
	postgresql_db = app_config.get( "postgres_db" )

	engine_url = engine_url_format.format(
		username=postgresql_username,
		password=postgresql_password,
		host=postgresql_host,
		db=postgresql_db
	)
	return create_engine( engine_url, pool_recycle=60, encoding="utf8" )


def create_scoped_db_session_maker( engine ):
	return scoped_session(sessionmaker(
		bind=engine,
		autocommit=False,
		autoflush=True
	))


class DatabaseBindingSpec(pinject.BindingSpec):
	def configure( self, bind ):
		pass

	@pinject.provides('db_engine')
	def provide_db_engine( self, app_config ):
		return get_refinery_engine( app_config )

	@pinject.provides('db_session_maker')
	def provide_db_session_maker( self, db_engine ):
		return create_scoped_db_session_maker( db_engine )
