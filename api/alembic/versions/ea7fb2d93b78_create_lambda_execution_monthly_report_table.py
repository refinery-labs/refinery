"""Add lambda execution monthly report table to the database

Revision ID: ea7fb2d93b78
Revises: 2ea8fd0edbea
Create Date: 2020-07-16 14:55:59.708033

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea7fb2d93b78'
down_revision = '2ea8fd0edbea'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'lambda_execution_monthly_reports',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column(
            'account_id',
            sa.Text(),
            sa.ForeignKey(
                "aws_accounts.account_id"
            ),
            index=True,
        ),
        sa.Column(
            "gb_seconds_used",
            sa.Float()
        ),
        sa.Column(
            "total_executions",
            sa.Integer()
        ),
        sa.Column(
            "timestamp",
            sa.Integer(),
            index=True
        )
    )


def downgrade():
    op.drop_table('lambda_execution_monthly_reports')
