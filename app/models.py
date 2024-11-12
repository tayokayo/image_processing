from datetime import datetime
from enum import Enum
from sqlalchemy.dialects.postgresql import JSONB
from .database import db

class ComponentStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class RoomScene(db.Model):
    __tablename__ = 'room_scenes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    file_path = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, primary_key=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    scene_metadata = db.Column(JSONB)  # Changed to JSONB for better performance
    review_completion_time = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Statistics columns
    total_components = db.Column(db.Integer, default=0)
    pending_components = db.Column(db.Integer, default=0)
    accepted_components = db.Column(db.Integer, default=0)
    rejected_components = db.Column(db.Integer, default=0)
    
    # Relationships
    components = db.relationship(
        "Component", 
        back_populates="room_scene",
        cascade="all, delete-orphan",
        lazy='select'
    )
    
    __table_args__ = (
        db.Index('idx_room_scenes_category_created', 'category', 'created_at'),
        db.Index('idx_room_scenes_metadata', 'scene_metadata', postgresql_using='gin'),
        db.Index('idx_scene_stats', 'total_components', 'review_completion_time'),
        {'postgresql_partition_by': 'RANGE (created_at)'}  # Add partitioning for large datasets
    )

class Component(db.Model):
    __tablename__ = 'components'
    
    id = db.Column(db.Integer, primary_key=True)
    room_scene_id = db.Column(db.Integer, db.ForeignKey('room_scenes.id', ondelete='CASCADE'), nullable=False)
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
    review_timestamp = db.Column(db.DateTime(timezone=True))
    reviewer_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, primary_key=True)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.utcnow)
    
    # Relationship
    room_scene = db.relationship("RoomScene", back_populates="components")
    
    __table_args__ = (
        db.Index('idx_components_scene_status', 'room_scene_id', 'status'),
        db.Index('idx_components_position', 'position_data', postgresql_using='gin'),
        db.Index('idx_component_review', 'status', 'review_timestamp'),
        db.Index('idx_component_confidence', 'confidence_score', 'component_type')
    )