"""saved block version hash

Revision ID: ec61883948f8
Revises: 895c817de6e5
Create Date: 2020-03-16 12:36:37.700282

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, LargeBinary


# revision identifiers, used by Alembic.
revision = 'ec61883948f8'
down_revision = '7a2896ce11ca'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('saved_block_versions',
                  Column('block_hash', LargeBinary, nullable=False, server_default='')
                  )


def downgrade():
    op.drop_column('saved_block_versions', 'block_hash')
