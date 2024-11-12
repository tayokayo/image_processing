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
from ..models import RoomScene, Component
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

    def __init__(self, sam_processor: SAMProcessor, error_logger: ErrorLogger, storage_base: str = 'storage'):
        """
        Initialize SceneHandler with required dependencies.
        
        Args:
            sam_processor: Instance of SAM model processor
            error_logger: Instance of error logger
            storage_base: Base directory for file storage
            db_session: SQLAlchemy session (optional, will use db_manager if None)
        """
        self.sam_processor = sam_processor
        self.error_logger = error_logger
        self.validator = SceneValidator(logger=error_logger.logger)
        self._stats_refresh_lock = Lock()
        
        # Storage setup
        self.storage_base = Path(storage_base)
        self.components_dir = self.storage_base / 'components'
        self.scenes_dir = self.storage_base / 'scenes'
        self.processed_dir = self.storage_base / 'processed'
        
        # Create directories if they don't exist
        for dir_path in [self.components_dir, self.scenes_dir, self.processed_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @lru_cache(maxsize=128)
    def get_cached_statistics(self, room_scene_id: int, cache_time: datetime) -> Optional[Dict]:
        """Get cached statistics with time-based invalidation"""
        return self.refresh_statistics(room_scene_id)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def refresh_statistics(self, room_scene_id: int) -> Optional[Dict[str, Any]]:
        """Refresh and retrieve statistics from materialized views with retry logic."""
        with self._stats_refresh_lock:
            try:
                with db_session() as session:
                    # Refresh materialized views concurrently
                    session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY detection_accuracy_stats_mv"))
                    session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY review_metrics_mv"))
                    
                    # Fetch combined statistics
                    stats = session.execute(text("""
                        SELECT 
                            d.total_components,
                            d.avg_confidence,
                            d.acceptance_rate,
                            d.type_distribution,
                            d.avg_review_time as detection_review_time,
                            r.total_reviews,
                            r.avg_review_time as overall_review_time,
                            r.median_confidence,
                            r.status_distribution
                        FROM detection_accuracy_stats_mv d
                        LEFT JOIN review_metrics_mv r ON TRUE
                        WHERE d.room_scene_id = :scene_id
                    """), {"scene_id": room_scene_id}).first()
                    
                    return dict(stats) if stats else None

            except Exception as e:
                self.error_logger.log_error(str(e), "StatisticsRefreshError")
                return None

    def process_scene(self, scene_path: str, category: str) -> ProcessingResult:
        """Process a scene image to detect and isolate components."""
        try:
            if not current_app:
                raise RuntimeError("No application context")
                
            validation_result = self.validator.validate_scene(scene_path)
            if not validation_result.is_valid:
                return ProcessingResult(
                    success=False,
                    message=validation_result.error_message,
                    error_details={'validation_error': validation_result.error_type}
                )

            scene_image = self._load_scene(scene_path)
            if scene_image is None:
                return ProcessingResult(
                    success=False,
                    message="Failed to load scene image",
                    error_details={'error_type': 'load_failure'}
                )

            with db_session() as session:
                # Create room scene with JSONB metadata
                metadata = self._extract_metadata(scene_image)
                room_scene = RoomScene(
                    name=Path(scene_path).stem,
                    category=category,
                    file_path=scene_path,
                    scene_metadata=metadata
                )
                session.add(room_scene)
                session.flush()  # Get ID without committing

                # Process components in nested transaction
                try:
                    with session.begin_nested():  # Create savepoint
                        components = self._isolate_components(scene_image, room_scene.id)
                        if not components:
                            raise ValueError("No components detected in scene")
                except Exception as e:
                    # Rollback to savepoint, keep room scene
                    return ProcessingResult(
                        success=False,
                        message="Component processing failed",
                        room_scene_id=room_scene.id,
                        components=[],
                        error_details={'component_error': str(e)}
                    )

                # Add statistics to successful result
                statistics = self.get_cached_statistics(room_scene.id, datetime.now())
                
                return ProcessingResult(
                    success=True,
                    message="Scene processed successfully",
                    room_scene_id=room_scene.id,
                    components=components,
                    statistics=statistics
                )

        except DatabaseError as e:
            return ProcessingResult(
                success=False,
                message=str(e),
                error_details={'database_error': str(e)}
            )
        except Exception as e:
            self.error_logger.log_error(str(e), "SceneProcessingError", scene_path)
            return ProcessingResult(
                success=False,
                message=f"Processing failed: {str(e)}",
                error_details={'exception': str(e)}
            )

    def _extract_metadata(self, image: np.ndarray) -> Dict:
        """Extract basic metadata from scene image"""
        return {
            'height': image.shape[0],
            'width': image.shape[1],
            'channels': image.shape[2],
            'mean_color': image.mean(axis=(0,1)).tolist()
        }

    def _isolate_components(self, image: np.ndarray, room_scene_id: int) -> List[Dict]:
        """Detect and isolate components from scene"""
        components = []
        
        try:
            # Set image in SAM predictor
            self.sam_processor.predictor.set_image(image)
            
            # Generate automatic masks
            masks = self._generate_masks(image)
            
            # Process each mask
            for idx, mask in enumerate(masks):
                processed_component = self._process_component(
                    image, 
                    mask, 
                    room_scene_id,
                    idx
                )
                if processed_component:
                    components.append(processed_component)
            
            return components
        
        except Exception as e:
            self.error_logger.log_error(str(e), "ComponentIsolationError")
            return []

    def _generate_masks(self, image: np.ndarray) -> List[np.ndarray]:
        """Generate masks for components using SAM"""
        h, w = image.shape[:2]
        points = self._create_points_grid(h, w)
        
        all_masks = []
        for point in points:
            masks, scores, _ = self.sam_processor.predictor.predict(
                point_coords=np.array([point]),
                point_labels=np.array([1]),
                multimask_output=True
            )
            
            if scores.size > 0:
                best_mask_idx = scores.argmax()
                all_masks.append(masks[best_mask_idx])
        
        return all_masks

    def _create_points_grid(self, height: int, width: int) -> List[Tuple[int, int]]:
        """Create a grid of points for mask generation"""
        step = max(100, min(height, width) // 8)  # Adaptive step size
        points = []
        for y in range(step, height-step, step):
            for x in range(step, width-step, step):
                points.append([x, y])
        return points

    def _get_component_bounds(self, mask: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Get bounding box for component mask"""
        try:
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)
            y1, y2 = np.where(rows)[0][[0, -1]]
            x1, x2 = np.where(cols)[0][[0, -1]]
            
            # Add padding
            padding = 10
            y1 = max(0, y1 - padding)
            y2 = min(mask.shape[0], y2 + padding)
            x1 = max(0, x1 - padding)
            x2 = min(mask.shape[1], x2 + padding)
            
            return (y1, y2, x1, x2)
        except Exception as e:
            self.error_logger.log_error(str(e), "BoundsCalculationError")
            return None

    def _process_component(self, image: np.ndarray, mask: np.ndarray, 
                        room_scene_id: int, index: int) -> Optional[Dict]:
        """Process individual component using its mask"""
        try:
            # Get component bounds
            bounds = self._get_component_bounds(mask)
            if not bounds:
                return None
                
            y1, y2, x1, x2 = bounds
            
            # Extract and save component image
            component_img = image[y1:y2, x1:x2].copy()
            component_path = str(self.components_dir / f"component_{room_scene_id}_{index}.jpg")
            cv2.imwrite(component_path, cv2.cvtColor(component_img, cv2.COLOR_RGB2BGR))
            
            # Use db_session for database operations
            with db_session() as session:
                # Create component record
                component = Component(
                    room_scene_id=room_scene_id,
                    name=f"Component {index}",
                    component_type="auto_detected", 
                    file_path=component_path,
                    position_data={
                        'bounds': bounds,
                        'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                        'size': [(x2 - x1), (y2 - y1)]
                    }
                )
                session.add(component)
                session.commit()
                
                return {
                    'component_id': component.id,
                    'bounds': bounds,
                    'path': component_path
                }
            
        except Exception as e:
            self.error_logger.log_error(str(e), "ComponentProcessingError")
            return None

    def _load_scene(self, scene_path: str) -> Optional[np.ndarray]:
        """Load and validate scene image"""
        try:
            scene_path = Path(scene_path)
            if not scene_path.exists():
                raise ValueError(f"Scene file does not exist: {scene_path}")
            
            if scene_path.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
                raise ValueError(f"Invalid file format: {scene_path.suffix}")
                
            image = cv2.imread(str(scene_path))
            if image is None:
                raise ValueError(f"Could not load image from {scene_path}")
                
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception as e:
            self.error_logger.log_error(str(e), "SceneLoadError", str(scene_path))
            return None
