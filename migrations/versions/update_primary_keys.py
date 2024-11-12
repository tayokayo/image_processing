from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'update_primary_keys_001'
down_revision = 'initial_schema_setup'  # This should point to your previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing tables
    op.execute("DROP TABLE IF EXISTS components CASCADE")
    op.execute("DROP TABLE IF EXISTS room_scenes CASCADE")
    
    # Create room_scenes with composite primary key
    op.create_table(
        'room_scenes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(255), nullable=False),
        sa.Column('scene_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('review_completion_time', sa.DateTime(), nullable=True),
        sa.Column('total_components', sa.Integer(), server_default='0'),
        sa.Column('pending_components', sa.Integer(), server_default='0'),
        sa.Column('accepted_components', sa.Integer(), server_default='0'),
        sa.Column('rejected_components', sa.Integer(), server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )
    
    # Create components with proper foreign key
    op.create_table(
        'components',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_scene_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('component_type', sa.String(50), nullable=False),
        sa.Column('position_data', postgresql.JSONB(), nullable=False),
        sa.Column('file_path', sa.String(255), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'ACCEPTED', 'REJECTED', name='component_status'), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('review_timestamp', sa.DateTime(), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['room_scene_id'], ['room_scenes.id'], ondelete='CASCADE')
    )

def downgrade():
    op.drop_table('components')
    op.drop_table('room_scenes')