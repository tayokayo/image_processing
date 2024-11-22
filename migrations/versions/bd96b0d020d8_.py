"""empty message

Revision ID: bd96b0d020d8
Revises: 014e4b14902c, merge_heads_001, update_primary_keys_001
Create Date: 2024-11-12 13:20:46.977202

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bd96b0d020d8'
down_revision = ('014e4b14902c', 'merge_heads_001', 'update_primary_keys_001')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
