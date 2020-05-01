"""Add billing exempt column

Revision ID: 319f703fc9d3
Revises: 7a2896ce11ca
Create Date: 2019-11-01 10:58:41.746322

"""
from alembic import op
from sqlalchemy import Column, Boolean

# revision identifiers, used by Alembic.
revision = '319f703fc9d3'
down_revision = '7a2896ce11ca'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('organizations',
                  Column('billing_exempt', Boolean(), nullable=False, server_default="False")
                  )


def downgrade():
    op.drop_column('organizations', 'billing_exempt')
