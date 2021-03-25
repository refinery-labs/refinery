"""Add deployment tag

Revision ID: 3fa1ed2e52ce
Revises: 62cd6e58c24d
Create Date: 2021-03-25 16:34:45.402174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3fa1ed2e52ce'
down_revision = '62cd6e58c24d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('deployments', sa.Column('tag', sa.Text, nullable=True))


def downgrade():
    op.drop_column('deployments', 'tag')
