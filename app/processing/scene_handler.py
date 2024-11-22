from threading import Lock
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from sqlalchemy import text
from functools import lru_cache
from datetime import datetime
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from .sam_processor import SAMProcessor
from .error_logger import ErrorLogger
from .scene_validator import SceneValidator, ValidationResult
from ..models import RoomScene, Component, ComponentStatus
from ..database import db, db_session
from flask import current_app
from app.exceptions import SceneProcessingError
from contextlib import contextmanager

class DatabaseError(Exception):
    """Base exception for database-related errors"""
    pass

@dataclass
class ProcessingResult:
    """Container for scene processing results"""
    success: bool
    message: str
    room_scene_id: Optional[int] = None
    components: List[Dict[str, Any]] = None
    error_details: Optional[Dict] = None
    statistics: Optional[Dict] = None  # New field for materialized view data

class SceneHandler:
    """Handles scene processing operations including component detection and isolation"""

    def __init__(self, sam_processor: SAMProcessor, error_logger: ErrorLogger):
        """
        Initialize SceneHandler with required dependencies.
        
        Args:
            sam_processor: Instance of SAM model processor
            error_logger: Instance of error logger
        """
        self.sam_processor = sam_processor
        self.error_logger = error_logger
        self.validator = SceneValidator()
        self._processing_lock = Lock()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def process_scene(self, scene_id: int) -> ProcessingResult:
        """Process a scene from database to detect and isolate components."""
        try:
            if not current_app:
                raise RuntimeError("No application context")

            with self._processing_lock:
                with db_session() as session:
                    # Load scene from database
                    scene = session.get(RoomScene, scene_id)
                    if not scene or not scene.image_data:
                        return ProcessingResult(
                            success=False,
                            message="Scene not found or no image data",
                            error_details={'error_type': 'invalid_scene'}
                        )

                    # Convert image data to numpy array
                    image_array = np.frombuffer(scene.image_data, np.uint8)
                    scene_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                    
                    # Validate image
                    validation_result = self.validator.validate_image(scene_image)
                    if not validation_result.is_valid:
                        return ProcessingResult(
                            success=False,
                            message=validation_result.error_message,
                            error_details={'validation_error': validation_result.error_type}
                        )

                    # Process components in nested transaction
                    try:
                        with session.begin_nested():
                            components = self._process_components(scene_image, scene)
                            if not components:
                                raise ValueError("No components detected in scene")
                            
                            # Update scene processing status
                            scene.processed = True
                            scene.updated_at = datetime.utcnow()
                            
                            session.commit()
                            
                            return ProcessingResult(
                                success=True,
                                message="Scene processed successfully",
                                room_scene_id=scene.id,
                                components=components,
                                statistics=self._get_scene_statistics(scene)
                            )
                    except Exception as e:
                        self.error_logger.log_error(
                            error_type="component_processing_error",
                            error_details=str(e),
                            scene_id=scene.id
                        )
                        return ProcessingResult(
                            success=False,
                            message="Component processing failed",
                            room_scene_id=scene.id,
                            error_details={'component_error': str(e)}
                        )

        except Exception as e:
            self.error_logger.log_error(
                error_type="scene_processing_error",
                error_details=str(e),
                scene_id=scene_id
            )
            return ProcessingResult(
                success=False,
                message=f"Scene processing failed: {str(e)}",
                error_details={'error_type': 'processing_error'}
            )

    def _process_components(
        self, 
        image: np.ndarray, 
        scene: RoomScene
    ) -> List[Dict[str, Any]]:
        """Process image to detect and create components."""
        detected_components = self.sam_processor.detect_components(image)
        components = []
        
        for comp_data in detected_components:
            component = Component(
                room_scene_id=scene.id,
                name=f"Component_{len(components) + 1}",
                component_type=comp_data['type'],
                position_data=comp_data['position'],
                confidence_score=comp_data['confidence'],
                status=ComponentStatus.PENDING
            )
            components.append(component)
        
        return [comp.to_dict() for comp in components]

    def _get_scene_statistics(self, scene: RoomScene) -> Dict[str, Any]:
        """Get current scene statistics."""
        return {
            'total_components': scene.total_components,
            'pending_components': scene.pending_components,
            'accepted_components': scene.accepted_components,
            'rejected_components': scene.rejected_components
        }
