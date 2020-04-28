"""block object stored as json

Revision ID: 39b78a88ec2b
Revises: 319f703fc9d3
Create Date: 2019-11-27 20:30:03.090471

"""
from alembic import op
import json
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Table, Column, Text

saved_block_versions = Table(
    'saved_block_versions',
    sa.MetaData(),
    Column('id', Text, primary_key=True),
    Column('block_object', Text),
    Column('block_object_json', JSONB),
)

# revision identifiers, used by Alembic.
revision = '39b78a88ec2b'
down_revision = '319f703fc9d3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('saved_block_versions',
                  Column('block_object_json', JSONB())
                  )
    conn = op.get_bind()

    for saved_block in conn.execute(saved_block_versions.select()):

        try:
            saved_block_json = json.loads(saved_block.block_object)
            conn.execute(
                saved_block_versions.update().where(
                    saved_block_versions.c.id == saved_block.id
                ).values(
                    block_object_json=saved_block_json
                )
            )
        except TypeError as e:
            print(("Failed to upgrade block: " + repr(saved_block)))


def downgrade():
    op.drop_column('saved_block_versions', 'block_object_json')
