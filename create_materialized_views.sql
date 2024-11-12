CREATE MATERIALIZED VIEW detection_accuracy_stats_mv AS
SELECT 
    COUNT(*) as total_components,
    AVG(confidence_score) as avg_confidence,
    SUM(CASE WHEN status = 'ACCEPTED' THEN 1 ELSE 0 END)::float / COUNT(*) as acceptance_rate,
    MIN(created_at) as first_detection,
    MAX(created_at) as last_detection,
    NOW() as last_refresh
FROM components;

CREATE INDEX idx_detection_accuracy_mv_refresh ON detection_accuracy_stats_mv(last_refresh);