from datetime import datetime
from enum import Enum
from .database import db

class ComponentStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class RoomScene(db.Model):
    __tablename__ = 'room_scenes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    category = db.Column(db.String, nullable=False)  # e.g., living_room, bedroom
    file_path = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scene_metadata = db.Column(db.JSON)  # Changed from 'metadata' to 'scene_metadata'
    review_completion_time = db.Column(db.DateTime, nullable=True)
    
    # New statistics columns
    total_components = db.Column(db.Integer, default=0)
    pending_components = db.Column(db.Integer, default=0)
    accepted_components = db.Column(db.Integer, default=0)
    rejected_components = db.Column(db.Integer, default=0)
    
    # Relationship with components
    components = db.relationship("Component", back_populates="room_scene", 
                               cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RoomScene(name='{self.name}', category='{self.category}')>"
    
    @property
    def review_progress(self):
        """Calculate the percentage of components reviewed"""
        if self.total_components == 0:
            return 0
        reviewed = self.accepted_components + self.rejected_components
        return (reviewed / self.total_components) * 100
    
    def update_statistics(self):
        """Update component statistics"""
        components = self.components
        self.total_components = len(components)
        self.pending_components = sum(1 for c in components if c.status == ComponentStatus.PENDING)
        self.accepted_components = sum(1 for c in components if c.status == ComponentStatus.ACCEPTED)
        self.rejected_components = sum(1 for c in components if c.status == ComponentStatus.REJECTED)
        db.session.commit()

class Component(db.Model):
    __tablename__ = 'components'
    
    id = db.Column(db.Integer, primary_key=True)
    room_scene_id = db.Column(db.Integer, db.ForeignKey('room_scenes.id'))
    name = db.Column(db.String, nullable=False)
    component_type = db.Column(db.String, nullable=False)  # e.g., furniture, wall_art
    position_data = db.Column(db.JSON)  # Store position and transformation data
    file_path = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # New status management columns
    status = db.Column(db.Enum(ComponentStatus), default=ComponentStatus.PENDING)
    confidence_score = db.Column(db.Float)
    review_timestamp = db.Column(db.DateTime)
    reviewer_notes = db.Column(db.String)
    
    # Relationship with room scene
    room_scene = db.relationship("RoomScene", back_populates="components")
    processed_results = db.relationship("ProcessedResult", back_populates="component",
                                      cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Component(name='{self.name}', type='{self.component_type}', status='{self.status}')>"
    
    def update_status(self, new_status: ComponentStatus, notes: str = None):
        """Update component status and related scene statistics"""
        self.status = new_status
        self.review_timestamp = datetime.utcnow()
        if notes:
            self.reviewer_notes = notes
        
        # Update scene statistics
        self.room_scene.update_statistics()

class ProcessedResult(db.Model):
    __tablename__ = 'processed_results'
    
    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    original_path = db.Column(db.String, nullable=False)
    processed_path = db.Column(db.String, nullable=False)
    mask_path = db.Column(db.String)
    processing_metadata = db.Column(db.JSON)  # This one is fine as it's not just 'metadata'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with component
    component = db.relationship("Component", back_populates="processed_results")
    
    def __repr__(self):
        return f"<ProcessedResult(component_id={self.component_id})>"