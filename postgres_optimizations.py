"""Optimize PostgreSQL schema and indexes

Revision ID: postgres_optimizations
Revises: dd094a98a27f
Create Date: 2024-03-19 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'postgres_optimizations'
down_revision = 'dd094a98a27f'
branch_labels = None
depends_on = None

def upgrade():
    # Convert JSON columns to JSONB
    with op.batch_alter_table('room_scenes') as batch_op:
        batch_op.alter_column('scene_metadata',
                            type_=postgresql.JSONB,
                            existing_type=sa.JSON())
        
        # Add GIN index for JSONB
        batch_op.create_index('idx_scene_metadata_gin',
                            ['scene_metadata'],
                            postgresql_using='gin')
        
        # Add composite index for common queries
        batch_op.create_index('idx_scene_stats',
                            ['category', 'total_components', 'review_completion_time'])

    with op.batch_alter_table('components') as batch_op:
        batch_op.alter_column('position_data',
                            type_=postgresql.JSONB,
                            existing_type=sa.JSON())
        
        # Add GIN index for JSONB
        batch_op.create_index('idx_position_data_gin',
                            ['position_data'],
                            postgresql_using='gin')
        
        # Add composite index for status queries
        batch_op.create_index('idx_component_review',
                            ['status', 'review_timestamp'])

def downgrade():
    with op.batch_alter_table('components') as batch_op:
        batch_op.drop_index('idx_component_review')
        batch_op.drop_index('idx_position_data_gin')
        batch_op.alter_column('position_data',
                            type_=sa.JSON(),
                            existing_type=postgresql.JSONB)

    with op.batch_alter_table('room_scenes') as batch_op:
        batch_op.drop_index('idx_scene_stats')
        batch_op.drop_index('idx_scene_metadata_gin')
        batch_op.alter_column('scene_metadata',
                            type_=sa.JSON(),
                            existing_type=postgresql.JSONB)