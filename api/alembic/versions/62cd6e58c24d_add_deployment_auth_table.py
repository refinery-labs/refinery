"""Add deployment_auth table

Revision ID: 62cd6e58c24d
Revises: 8e249aada603
Create Date: 2021-03-16 19:15:10.138582

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62cd6e58c24d'
down_revision = '8e249aada603'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('deployment_auth',
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('org_id', sa.CHAR(length=36), nullable=True),
        sa.Column('secret', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('secret')
