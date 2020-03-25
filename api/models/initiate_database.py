import yaml
import os

from sqlalchemy import create_engine

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import or_ as sql_or
from sqlalchemy import Column, Integer, String, func, update, Text, Binary, Boolean, BigInteger, event, select, exc, CHAR, ForeignKey, JSON, Table
from sqlalchemy.orm import sessionmaker, scoped_session, relationship, synonym
from contextlib import contextmanager

from config.app_config import global_app_config

engine_url_format = "postgresql://{username}:{password}@{host}/{db}?client_encoding=utf8"


def create_scoped_db_session_maker(app_config):
	if app_config.get_if_exists( "SKIP_DATABASE_CONNECT" ):
		return None

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
	engine = create_engine( engine_url, pool_recycle=60, encoding="utf8" )

	return scoped_session(sessionmaker(
		bind=engine,
		autocommit=False,
		autoflush=True
	))


# TODO THIS IS TEMPORARY UNTIL WE MAKE A DENT IN DEP INJECTION
DBSession = create_scoped_db_session_maker(global_app_config)