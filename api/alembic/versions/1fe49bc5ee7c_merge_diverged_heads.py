"""Merge diverged heads

Revision ID: 1fe49bc5ee7c
Revises: 895c817de6e5, b1c3d08b9adc
Create Date: 2020-08-28 15:33:06.641815

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1fe49bc5ee7c'
down_revision = ('895c817de6e5', 'b1c3d08b9adc')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
