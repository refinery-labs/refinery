"""Add Shared Files to Saved Blocks database model

Revision ID: 7a2896ce11ca
Revises: 
Create Date: 2019-10-10 14:49:01.468927

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, func, update, Text, Binary, Boolean, BigInteger, event, select, exc, CHAR, ForeignKey, JSON, Table


# revision identifiers, used by Alembic.
revision = '7a2896ce11ca'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('saved_block_versions',
        Column('shared_files', JSON())
    )


def downgrade():
    op.drop_column('saved_block_versions', 'shared_files')
