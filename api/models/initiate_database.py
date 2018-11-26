import yaml
import os

# Debugging shunt for setting environment variables from yaml
try:
    with open( "config.yaml", "r" ) as file_handler:
        settings = yaml.safe_load(
            file_handler.read()
        )
        for key, value in settings.iteritems():
            os.environ[ key ] = str( value )
except:
    print( "No config.yaml specified, assuming environmental variables are all set!" )

from sqlalchemy import create_engine
engine = create_engine( "postgresql://" + os.environ.get( "postgreql_username" ) + ":" + os.environ.get( "postgreql_password" ) + "@" + os.environ.get( "postgresql_host" ) + "/" + os.environ.get( "postgres_db" ) + "?client_encoding=utf8", pool_recycle=60, encoding="utf8")
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Column, Integer, String, func, update, Text, Binary, Boolean, BigInteger, event, select, exc, CHAR, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
Session = scoped_session(sessionmaker(bind=engine))
session = Session()
