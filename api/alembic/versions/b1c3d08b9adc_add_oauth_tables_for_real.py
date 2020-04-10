"""add oauth tables, for real

Revision ID: b1c3d08b9adc
Revises: b3ec98048997
Create Date: 2020-02-18 13:06:28.606332

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b1c3d08b9adc'
down_revision = 'b3ec98048997'
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		'user_oauth_accounts',
		sa.Column( 'id', sa.TEXT(), nullable=False ),
		sa.Column( 'provider', sa.Enum( 'github', 'google', name='oauthprovider' ), nullable=False ),
		sa.Column( 'user_id', sa.TEXT(), nullable=False ),
		sa.Column( 'provider_unique_id', sa.TEXT(), nullable=False ),
		sa.ForeignKeyConstraint( ['user_id'], ['users.id'], ),
		sa.PrimaryKeyConstraint( 'id' )
	)
	op.create_index(
		'idx_provider__user',
		'user_oauth_accounts',
		['provider', 'user_id'],
		unique=True
	)
	op.create_index(
		'idx_provider__provider_unique_id',
		'user_oauth_accounts',
		['provider', 'provider_unique_id'],
		unique=True
	)
	op.create_table(
		'user_oauth_data_records',
		sa.Column( 'id', sa.TEXT(), nullable=False ),
		sa.Column( 'oauth_token', sa.Text(), nullable=False ),
		sa.Column( 'json_data', postgresql.JSONB( astext_type=sa.Text() ), nullable=False ),
		sa.Column( 'timestamp', sa.Integer(), nullable=False ),
		sa.Column( 'oauth_account_id', sa.TEXT(), nullable=False ),
		sa.ForeignKeyConstraint( ['oauth_account_id'], ['user_oauth_accounts.id'], ),
		sa.PrimaryKeyConstraint( 'id' )
	)
	op.create_index(
		'idx_oauth_account_id__timestamp',
		'user_oauth_data_records',
		['oauth_account_id', sa.text( u'timestamp DESC' )],
		unique=False
	)


def downgrade():
	op.drop_index( 'idx_oauth_account_id__timestamp', table_name='user_oauth_data_records' )
	op.drop_table( 'user_oauth_data_records' )
	op.drop_index( 'idx_provider__user', table_name='user_oauth_accounts' )
	op.drop_index( 'idx_provider__provider_unique_id', table_name='user_oauth_accounts' )
	op.drop_table( 'user_oauth_accounts' )
	op.execute( 'DROP TYPE oauthprovider' )
