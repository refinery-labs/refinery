"""Add tier column to users table
Revision ID: 820815b85cf7
Revises: b1c3d08b9adc
Create Date: 2020-02-19 11:05:17.089495
"""
from alembic import op

import sqlalchemy as sa

from models.users import RefineryUserTier

# revision identifiers, used by Alembic.
revision = '820815b85cf7'
down_revision = 'b1c3d08b9adc'
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		'_dummy',
		sa.Column('id', sa.Integer, primary_key=True),
		sa.Column('status', sa.Enum(RefineryUserTier))
	)
	op.drop_table('_dummy')

	op.add_column(
		'users',
		sa.Column(
			'tier',
			sa.Enum(RefineryUserTier),
			nullable=True,
			# Set default to paid since all users before free-tier
			# will indeed be paid users
			server_default="PAID"
		)
	)

	# Now modify the column to not allow null
	op.alter_column(
		'users',
		'tier',
		nullable=False
	)

def downgrade():
	op.drop_column('users', 'tier')