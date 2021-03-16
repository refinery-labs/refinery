"""Add deployment stage column

Revision ID: 8e249aada603
Revises: c1174c6e02ed
Create Date: 2021-03-09 18:12:41.124619

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy import Enum, Column, Integer
from sqlalchemy.dialects import postgresql

from data_types.deployment_stages import DeploymentStages

revision = '8e249aada603'
down_revision = 'c1174c6e02ed'
branch_labels = None
depends_on = None

def upgrade():
    deployment_stages = postgresql.ENUM(DeploymentStages, name="deployment_stages")
    deployment_stages.create(op.get_bind(), checkfirst=True)
    op.add_column('deployments', sa.Column('stage', deployment_stages, default=DeploymentStages.prod.value))


def downgrade():
    op.drop_column('deployments', 'stage')
    deployment_stages = postgresql.ENUM(DeploymentStages, name="deployment_stages")
    deployment_stages.drop(op.get_bind())