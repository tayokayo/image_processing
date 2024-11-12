from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'initial_schema_setup'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing tables if they exist
    op.execute("DROP MATERIALIZED VIEW IF EXISTS review_metrics_mv CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS detection_accuracy_stats_mv CASCADE")
    op.execute("DROP TABLE IF EXISTS components CASCADE")
    op.execute("DROP TABLE IF EXISTS room_scenes CASCADE")
    
    # 2. Create initial tables with JSONB and proper indexes
    op.create_table(
        'room_scenes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(255), nullable=False),
        sa.Column('scene_metadata', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        sa.Column('review_completion_time', sa.DateTime()),
        sa.Column('total_components', sa.Integer(), default=0),
        sa.Column('pending_components', sa.Integer(), default=0),
        sa.Column('accepted_components', sa.Integer(), default=0),
        sa.Column('rejected_components', sa.Integer(), default=0),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 3. Create indexes for room_scenes
    op.create_index('idx_scene_metadata_gin', 'room_scenes', ['scene_metadata'], postgresql_using='gin')
    op.create_index('idx_scene_stats', 'room_scenes', ['category', 'total_components', 'review_completion_time'])
    
    # 4. Create components table with all required columns and indexes
    op.create_table(
        'components',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_scene_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('component_type', sa.String(50), nullable=False),
        sa.Column('position_data', postgresql.JSONB(), nullable=False),
        sa.Column('file_path', sa.String(255), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'ACCEPTED', 'REJECTED', name='component_status'), default='PENDING'),
        sa.Column('confidence_score', sa.Float()),
        sa.Column('review_timestamp', sa.DateTime()),
        sa.Column('reviewer_notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['room_scene_id'], ['room_scenes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 5. Create indexes for components
    op.create_index('idx_position_data_gin', 'components', ['position_data'], postgresql_using='gin')
    op.create_index('idx_component_review', 'components', ['status', 'review_timestamp'])
    op.create_index('idx_component_confidence', 'components', ['confidence_score', 'component_type'])
    
    # 6. Create materialized views
    op.execute("""
        CREATE MATERIALIZED VIEW detection_accuracy_stats_mv AS
        WITH component_stats AS (
            SELECT 
                COUNT(*) as total_components,
                AVG(confidence_score) as avg_confidence,
                SUM(CASE WHEN status = 'ACCEPTED' THEN 1 ELSE 0 END)::float / COUNT(*) as acceptance_rate,
                MIN(created_at) as first_detection,
                MAX(created_at) as last_detection,
                jsonb_object_agg(component_type, COUNT(*)) as type_distribution,
                AVG(EXTRACT(EPOCH FROM (review_timestamp - created_at))) as avg_review_time
            FROM components
            GROUP BY room_scene_id
        )
        SELECT 
            *,
            NOW() as last_refresh
        FROM component_stats;

        CREATE UNIQUE INDEX idx_detection_accuracy_mv_refresh ON detection_accuracy_stats_mv(last_refresh);
        CREATE INDEX idx_detection_accuracy_mv_confidence ON detection_accuracy_stats_mv(avg_confidence);
    """)

    op.execute("""
        CREATE MATERIALIZED VIEW review_metrics_mv AS
        SELECT 
            COUNT(*) as total_reviews,
            AVG(EXTRACT(EPOCH FROM (review_timestamp - created_at))) as avg_review_time,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY confidence_score) as median_confidence,
            jsonb_object_agg(status, COUNT(*)) as status_distribution,
            NOW() as last_refresh
        FROM components
        WHERE review_timestamp IS NOT NULL;

        CREATE UNIQUE INDEX idx_review_metrics_mv_refresh ON review_metrics_mv(last_refresh);
    """)

def downgrade():
    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS review_metrics_mv CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS detection_accuracy_stats_mv CASCADE")
    
    # Drop tables
    op.drop_table('components')
    op.drop_table('room_scenes')
    
    # Drop enum type
    op.execute("DROP TYPE component_status")