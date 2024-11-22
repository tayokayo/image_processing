"""merge multiple heads

Revision ID: merge_heads_001
Revises: initial_schema_setup, postgres_optimizations
Create Date: 2024-03-19 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'merge_heads_001'
down_revision = ('initial_schema_setup', 'postgres_optimizations')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass 