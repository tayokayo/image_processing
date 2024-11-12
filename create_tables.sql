-- Drop existing objects if they exist
DROP MATERIALIZED VIEW IF EXISTS review_metrics_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS detection_accuracy_stats_mv CASCADE;
DROP TABLE IF EXISTS components CASCADE;
DROP TABLE IF EXISTS room_scenes CASCADE;
DROP TYPE IF EXISTS component_status CASCADE;

-- Create enum type
CREATE TYPE component_status AS ENUM ('PENDING', 'ACCEPTED', 'REJECTED');

-- Create room_scenes table
CREATE TABLE room_scenes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    scene_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    review_completion_time TIMESTAMP,
    total_components INTEGER DEFAULT 0,
    pending_components INTEGER DEFAULT 0,
    accepted_components INTEGER DEFAULT 0,
    rejected_components INTEGER DEFAULT 0
);

-- Create indexes for room_scenes
CREATE INDEX idx_scene_metadata_gin ON room_scenes USING gin(scene_metadata);
CREATE INDEX idx_scene_stats ON room_scenes(category, total_components, review_completion_time);

-- Create components table
CREATE TABLE components (
    id SERIAL PRIMARY KEY,
    room_scene_id INTEGER NOT NULL REFERENCES room_scenes(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    component_type VARCHAR(50) NOT NULL,
    position_data JSONB NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    status component_status DEFAULT 'PENDING',
    confidence_score FLOAT,
    review_timestamp TIMESTAMP,
    reviewer_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for components
CREATE INDEX idx_position_data_gin ON components USING gin(position_data);
CREATE INDEX idx_component_review ON components(status, review_timestamp);
CREATE INDEX idx_component_confidence ON components(confidence_score, component_type);

-- Create materialized views
CREATE MATERIALIZED VIEW detection_accuracy_stats_mv AS
WITH component_stats AS (
    SELECT 
        room_scene_id,
        COUNT(*) as total_components,
        AVG(confidence_score) as avg_confidence,
        SUM(CASE WHEN status = 'ACCEPTED' THEN 1 ELSE 0 END)::float / COUNT(*) as acceptance_rate,
        MIN(created_at) as first_detection,
        MAX(created_at) as last_detection,
        AVG(EXTRACT(EPOCH FROM (review_timestamp - created_at))) as avg_review_time
    FROM components
    GROUP BY room_scene_id
),
type_counts AS (
    SELECT 
        room_scene_id,
        jsonb_object_agg(component_type, type_count) as type_distribution
    FROM (
        SELECT room_scene_id, component_type, COUNT(*) as type_count
        FROM components
        GROUP BY room_scene_id, component_type
    ) t
    GROUP BY room_scene_id
)
SELECT 
    cs.*,
    tc.type_distribution,
    NOW() as last_refresh
FROM component_stats cs
JOIN type_counts tc USING (room_scene_id);

CREATE UNIQUE INDEX idx_detection_accuracy_mv_refresh ON detection_accuracy_stats_mv(last_refresh);
CREATE INDEX idx_detection_accuracy_mv_confidence ON detection_accuracy_stats_mv(avg_confidence);

-- Create review metrics materialized view
CREATE MATERIALIZED VIEW review_metrics_mv AS
WITH status_counts AS (
    SELECT status, COUNT(*) as count
    FROM components
    WHERE review_timestamp IS NOT NULL
    GROUP BY status
)
SELECT 
    (SELECT COUNT(*) FROM components WHERE review_timestamp IS NOT NULL) as total_reviews,
    AVG(EXTRACT(EPOCH FROM (review_timestamp - created_at))) as avg_review_time,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY confidence_score) as median_confidence,
    (SELECT jsonb_object_agg(status, count) FROM status_counts) as status_distribution,
    NOW() as last_refresh
FROM components
WHERE review_timestamp IS NOT NULL;

CREATE UNIQUE INDEX idx_review_metrics_mv_refresh ON review_metrics_mv(last_refresh);