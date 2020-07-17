"""Add is_frozen column to AWS accounts table
Revision ID: 2ea8fd0edbea
Revises: 820815b85cf7
Create Date: 2020-02-20 12:31:08.669968
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2ea8fd0edbea'
down_revision = '820815b85cf7'
branch_labels = None
depends_on = None


def upgrade():
	op.add_column(
		"aws_accounts",
		sa.Column(
			"is_frozen",
			sa.Boolean,
			default=False
		)
	)
	op.execute("UPDATE aws_accounts SET is_frozen = false")


def downgrade():
	op.drop_column(
		"aws_accounts",
		"is_frozen"
	)