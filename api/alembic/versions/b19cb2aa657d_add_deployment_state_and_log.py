"""Add deployment state and log

Revision ID: b19cb2aa657d
Revises: 3fa1ed2e52ce
Create Date: 2021-06-02 23:59:42.756620

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy.dialects import postgresql

from data_types.deployment_stages import DeploymentStates

revision = 'b19cb2aa657d'
down_revision = '3fa1ed2e52ce'
branch_labels = None
depends_on = None


def upgrade():
    deployment_states = postgresql.ENUM(DeploymentStates, name="deployment_stages")
    deployment_states.create(op.get_bind(), checkfirst=True)
    op.add_column('deployments', sa.Column('state', deployment_states, default=DeploymentStates.not_started.value))
    op.add_column('deployments', sa.Column('log', sa.Text()))


def downgrade():
    op.drop_column('deployments', 'state')
    op.drop_column('deployments', 'log')
    deployment_states = postgresql.ENUM(DeploymentStates, name="deployment_states")
    deployment_states.drop(op.get_bind())
