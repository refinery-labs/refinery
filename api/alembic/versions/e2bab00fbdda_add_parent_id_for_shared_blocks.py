"""add parent id for shared blocks

Revision ID: e2bab00fbdda
Revises: 39b78a88ec2b
Create Date: 2019-11-30 16:48:04.496924

"""
from alembic import op
from sqlalchemy import Column, Text


# revision identifiers, used by Alembic.
revision = 'e2bab00fbdda'
down_revision = '39b78a88ec2b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('saved_blocks',
      Column('parent_id', Text())
      )


def downgrade():
    op.drop_column('saved_blocks', 'parent_id')
