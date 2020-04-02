"""create task locks table

Revision ID: 895c817de6e5
Revises: 39b78a88ec2b
Create Date: 2020-03-04 19:41:56.803946

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '895c817de6e5'
down_revision = '39b78a88ec2b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'task_locks',
        sa.Column('task_id', sa.Text(), primary_key=True),
        sa.Column('expiry', sa.DateTime()),
        sa.Column('locked', sa.Boolean()),
    )


def downgrade():
    op.drop_table('task_locks')