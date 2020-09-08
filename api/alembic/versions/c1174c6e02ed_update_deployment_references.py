"""update deployment references

Revision ID: c1174c6e02ed
Revises: 7bccb5021891
Create Date: 2020-09-08 16:12:57.055485

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1174c6e02ed'
down_revision = '7bccb5021891'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(None, 'deployment_log', 'organizations', ['org_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'deployment_log', type_='foreignkey')
    # ### end Alembic commands ###
