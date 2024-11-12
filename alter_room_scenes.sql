-- First drop all dependent objects
DROP TABLE IF EXISTS components CASCADE;
DROP TABLE IF EXISTS room_scenes CASCADE;

-- Recreate room_scenes with the correct structure
CREATE TABLE room_scenes (
    id SERIAL,
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
    rejected_components INTEGER DEFAULT 0,
    PRIMARY KEY (id, created_at)
);

-- Create components with matching structure
CREATE TABLE components (
    id SERIAL,
    room_scene_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    component_type VARCHAR(50) NOT NULL,
    position_data JSONB NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    status component_status DEFAULT 'PENDING',
    confidence_score FLOAT,
    review_timestamp TIMESTAMP,
    reviewer_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at),
    FOREIGN KEY (room_scene_id, created_at) REFERENCES room_scenes (id, created_at) ON DELETE CASCADE
);

-- Recreate indexes
CREATE INDEX idx_scene_metadata_gin ON room_scenes USING gin(scene_metadata);
CREATE INDEX idx_scene_stats ON room_scenes(category, total_components, review_completion_time);
CREATE INDEX idx_room_scenes_created_at ON room_scenes(created_at);