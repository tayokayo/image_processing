import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from .sam_processor import SAMProcessor
from .error_logger import ErrorLogger
from .scene_validator import SceneValidator, ValidationResult
from ..models import RoomScene, Component
from ..database import db_manager
from .. import db
from flask import current_app

@dataclass
class ProcessingResult:
    """Container for scene processing results"""
    success: bool
    message: str
    room_scene_id: Optional[int] = None
    components: List[Dict[str, Any]] = None
    error_details: Optional[Dict] = None

class SceneHandler:
    """Handles scene processing operations including component detection and isolation"""

    def __init__(self, sam_processor: SAMProcessor, error_logger: ErrorLogger, storage_base: str = 'storage', db_session=None):
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
        self.storage_base = storage_base
        self.validator = SceneValidator(logger=error_logger.logger)
        
        # Set up storage paths using provided base
        self.storage_base = Path(storage_base)
        self.components_dir = self.storage_base / 'components'
        self.scenes_dir = self.storage_base / 'scenes'
        self.processed_dir = self.storage_base / 'processed'
        
        # Create directories if they don't exist
        for dir_path in [self.components_dir, self.scenes_dir, self.processed_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Use provided session or default to Flask-SQLAlchemy session
        self.db_session = db_session if db_session is not None else db.session

    def process_scene(self, scene_path: str, category: str) -> ProcessingResult:
        """
        Process a scene image to detect and isolate components.
        
        Args:
            scene_path: Path to the scene image
            category: Category of the scene (e.g., 'living_room')
            
        Returns:
            ProcessingResult containing processing status and results
        """
        try:
            # Ensure we're in an application context
            if not current_app:
                raise RuntimeError("No application context")
                
            # Validate scene
            validation_result = self.validator.validate_scene(scene_path)
            if not validation_result.is_valid:
                return ProcessingResult(
                    success=False,
                    message=validation_result.error_message,
                    error_details={'validation_error': validation_result.error_type}
                )

            # Load scene
            scene_image = self._load_scene(scene_path)
            if scene_image is None:
                return ProcessingResult(
                    success=False,
                    message="Failed to load scene image",
                    error_details={'error_type': 'load_failure'}
                )

            # Extract metadata and create room scene record
            metadata = self._extract_metadata(scene_image)
            
            # Create room scene using Flask-SQLAlchemy session
            room_scene = RoomScene(
                name=Path(scene_path).stem,
                category=category,
                file_path=scene_path,
                scene_metadata=metadata
            )
            self.db_session.add(room_scene)
            self.db_session.commit()

            # Process components
            components = self._isolate_components(scene_image, room_scene.id)
            if not components:
                return ProcessingResult(
                    success=False,
                    message="No components detected in scene",
                    room_scene_id=room_scene.id,
                    components=[]
                )

            return ProcessingResult(
                success=True,
                message="Scene processed successfully",
                room_scene_id=room_scene.id,
                components=components
            )

        except Exception as e:
            self.error_logger.log_error(str(e), "SceneProcessingError", scene_path)
            if 'room_scene' in locals():
                self.db_session.rollback()
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

    def _create_room_scene(self, scene_path: str, category: str, metadata: Dict) -> RoomScene:
        """Create and save room scene record"""
        room_scene = RoomScene(
            name=Path(scene_path).stem,
            category=category,
            file_path=scene_path,
            scene_metadata=metadata
        )
        self.db.add(room_scene)
        self.db.commit()
        return room_scene

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
            # Apply mask to image
            masked_image = image.copy()
            masked_image[~mask] = [255, 255, 255]  # White background
            
            # Get component bounds
            bounds = self._get_component_bounds(mask)
            if bounds is None:
                return None
            
            # Crop component
            y1, y2, x1, x2 = bounds
            cropped_component = masked_image[y1:y2, x1:x2]
            
            # Save component image
            component_filename = f"component_{room_scene_id}_{index}.png"
            component_path = str(self.components_dir / component_filename)
            cv2.imwrite(component_path, cv2.cvtColor(cropped_component, cv2.COLOR_RGB2BGR))
            
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
            self.db_session.add(component)
            self.db_session.commit()
            
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
