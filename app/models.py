from datetime import datetime
from enum import Enum
from sqlalchemy.dialects.postgresql import JSONB
from .database import db

class ComponentStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class RoomScene(db.Model):
    __tablename__ = 'room_scenes'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, primary_key=True, default=datetime.utcnow)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    image_data = db.Column(db.LargeBinary)
    scene_metadata = db.Column(JSONB, server_default='{}')
    updated_at = db.Column(db.DateTime)
    review_completion_time = db.Column(db.DateTime)
    processed = db.Column(db.Boolean, default=False)
    
    # Statistics columns
    total_components = db.Column(db.Integer, server_default='0')
    pending_components = db.Column(db.Integer, server_default='0')
    accepted_components = db.Column(db.Integer, server_default='0')
    rejected_components = db.Column(db.Integer, server_default='0')
    
    # Relationships
    components = db.relationship(
        "Component", 
        back_populates="room_scene",
        cascade="all, delete-orphan",
        lazy='select'
    )
    
    __table_args__ = (
        db.Index('idx_scene_metadata_gin', 'scene_metadata', postgresql_using='gin'),
        db.Index('idx_scene_stats', 'category', 'total_components', 'review_completion_time'),
        db.Index('idx_room_scenes_created_at', 'created_at')
    )

class Component(db.Model):
    __tablename__ = 'components'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, primary_key=True, default=datetime.utcnow)
    room_scene_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    component_type = db.Column(db.String(50), nullable=False)
    position_data = db.Column(JSONB, nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    status = db.Column(
        db.Enum(ComponentStatus, name='component_status', 
                values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ComponentStatus.PENDING
    )
    confidence_score = db.Column(db.Float)
    review_timestamp = db.Column(db.DateTime)
    reviewer_notes = db.Column(db.Text)
    
    # Relationships
    room_scene = db.relationship("RoomScene", back_populates="components")
    
    __table_args__ = (
        db.Index('idx_position_data_gin', 'position_data', postgresql_using='gin'),
        db.Index('idx_component_review', 'status', 'review_timestamp'),
        db.Index('idx_component_confidence', 'confidence_score', 'component_type'),
        db.ForeignKeyConstraint(
            ['room_scene_id', 'created_at'],
            ['room_scenes.id', 'room_scenes.created_at'],
            ondelete='CASCADE'
        )
    )