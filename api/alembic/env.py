
# import os
# import sys
#
# parent_dir = os.path.abspath(os.path.join(os.getcwd(), ".."))
# sys.path.append(parent_dir)

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# from models.initiate_database import *
from models.saved_block import SavedBlock
from models.saved_block_version import SavedBlockVersion
from models.project_versions import ProjectVersion
from models.projects import Project
from models.organizations import Organization
from models.users import User
from models.email_auth_tokens import EmailAuthToken
from models.aws_accounts import AWSAccount
from models.deployments import Deployment
from models.project_config import ProjectConfig
from models.cached_billing_collections import CachedBillingCollection
from models.cached_billing_items import CachedBillingItem
from models.terraform_state_versions import TerraformStateVersion
from models.state_logs import StateLog

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = [
    SavedBlock.metadata,
    SavedBlockVersion.metadata,
    ProjectVersion.metadata,
    Project.metadata,
    Organization.metadata,
    User.metadata,
    EmailAuthToken.metadata,
    AWSAccount.metadata,
    Deployment.metadata,
    ProjectConfig.metadata,
    CachedBillingCollection.metadata,
    CachedBillingItem.metadata,
    TerraformStateVersion.metadata,
    StateLog.metadata,
]

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
