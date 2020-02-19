"""Add tier column to users table

Revision ID: 820815b85cf7
Revises: 39b78a88ec2b
Create Date: 2020-02-19 11:05:17.089495

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '820815b85cf7'
down_revision = '39b78a88ec2b'
branch_labels = None
depends_on = None


def upgrade():
	op.add_column(
		'users',
		sa.Column(
			'tier',
			sa.Text,
			nullable=True
		)
	)

	# Set default to paid since all users before free-tier
	# will indeed be paid users
	op.execute("UPDATE users SET tier = 'paid'")

	# Now modify the column to not allow null
	op.alter_column(
		'users',
		'tier',
		nullable=False
	)

def downgrade():
    op.drop_column('users', 'tier')