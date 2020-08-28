"""add deployment log

Revision ID: 144a0c0eb992
Revises: 1fe49bc5ee7c
Create Date: 2020-08-28 16:26:32.486961

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '144a0c0eb992'
down_revision = '1fe49bc5ee7c'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'deployment_log',
        sa.Column('id', sa.Text(length=36), primary_key=True),
        sa.Column('org_id', sa.Text(length=36)),
        sa.Column('timestamp', sa.DateTime()),
    )


def downgrade():
    op.drop_table('deployment_log')
