"""add deployment log

Revision ID: 22b49dd64768
Revises: 1fe49bc5ee7c
Create Date: 2020-08-28 16:31:42.147083

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '22b49dd64768'
down_revision = '1fe49bc5ee7c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('deployment_log',
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('org_id', sa.CHAR(length=36), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('deployment_log')
