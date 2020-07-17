"""empty message

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
        'lambda_executions',
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
            "log_name",
            sa.Text()
        ),
        sa.Column(
            "log_stream",
            sa.Text()
        ),
        sa.Column(
            "lambda_name",
            sa.Text()
        ),
        sa.Column(
            "raw_line",
            sa.Text()
        ),
        sa.Column(
            "execution_timestamp",
            sa.BigInteger()
        ),
        sa.Column(
            "execution_timestamp_ms",
            sa.BigInteger()
        ),
        sa.Column(
            "duration",
            sa.Float()
        ),
        sa.Column(
            "billed_duration",
            sa.BigInteger()
        ),
        sa.Column(
            "memory_size",
            sa.BigInteger()
        ),
        sa.Column(
            "max_memory_used",
            sa.BigInteger()
        ),
        sa.Column(
            "report_requestid",
            sa.Text()
        ),
        sa.Column(
            "timestamp",
            sa.Integer(),
            index=True
        )
    )


def downgrade():
    op.drop_table('lambda_executions')
