from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create materialized view for detection accuracy stats
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

    # Create materialized view for review metrics
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