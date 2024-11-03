import unittest
import os
import shutil
import logging
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

from app.processing.scene_handler import SceneHandler
from app.processing.scene_validator import SceneValidator, ValidationResult
from app.processing.sam_processor import SAMProcessor
from app.processing.error_logger import ErrorLogger
from app.database import db_manager
from app.models import RoomScene, Component

class TestSceneProcessing(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Create test directories
        self.test_dir = Path('test_storage')
        self.scenes_dir = self.test_dir / 'scenes'
        self.components_dir = self.test_dir / 'components'
        self.processed_dir = self.test_dir / 'processed'
        
        # Create all directories
        for dir_path in [self.scenes_dir, self.components_dir, self.processed_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create test scene image
        self.test_scene_path = self.scenes_dir / 'test_scene.jpg'
        self._create_test_scene()
        
        # Initialize components
        self.error_logger = ErrorLogger(self.test_dir / 'logs')
        self.sam_processor = SAMProcessor(os.getenv('SAM_MODEL_PATH'))
        self.sam_processor.load_model()
        
        # Initialize scene handler with proper paths
        self.scene_handler = SceneHandler(
            sam_processor=self.sam_processor,
            error_logger=self.error_logger,
            storage_base=str(self.test_dir)
        )
        
        # Initialize validator
        self.validator = SceneValidator(logger=self.error_logger.logger)
        
        # Initialize database
        db_manager.init_db()
        self.db = db_manager.get_session()

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up database
        self.db.close()
        db_manager.cleanup_session()
        
        # Clean up test directories
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _create_test_scene(self):
        """Create a test scene with simple shapes for component detection"""
        # Create a 1920x1080 image with light gray background instead of white
        image = np.full((1080, 1920, 3), 200, dtype=np.uint8)  # Changed from 255 to 200
        
        # Draw some shapes that could be components
        # Rectangle (simulating a table)
        cv2.rectangle(image, (400, 300), (800, 500), (150, 75, 0), -1)
        
        # Circle (simulating a lamp)
        cv2.circle(image, (1200, 400), 100, (0, 0, 0), -1)
        
        # Add some texture/contrast for quality validation
        cv2.putText(image, "Room Scene", (100, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
        
        # Ensure directory exists
        self.scenes_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the image with high quality
        cv2.imwrite(str(self.test_scene_path), image, 
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        print(f"Test scene created at: {self.test_scene_path}")
        print(f"Image shape: {image.shape}")

        # Convert NumPy values to native Python types before storing
        def convert_to_native_types(data):
            if isinstance(data, (np.int64, np.int32, np.int16, np.int8)):
                return int(data)
            if isinstance(data, (np.float64, np.float32)):
                return float(data)
            if isinstance(data, (tuple, list)):
                return [convert_to_native_types(item) for item in data]
            if isinstance(data, dict):
                return {key: convert_to_native_types(value) for key, value in data.items()}
            return data

        # When creating position_data, convert the values
        position_data = {
            'bounds': tuple(int(x) for x in (0, 1079, 0, 1908)),
            'center': [int(x) for x in [954, 539]],
            'size': [int(x) for x in [1908, 1079]]
        }
        
        # Store position_data for use in tests
        self.test_scene_position_data = position_data

    def test_scene_validation(self):
        """Test scene validation"""
        validation_result = self.validator.validate_scene(str(self.test_scene_path))
        
        # Print validation details for debugging
        if not validation_result.is_valid:
            print(f"\nValidation failed: {validation_result.error_message}")
            if validation_result.details:
                print(f"Details: {validation_result.details}")
        
        self.assertTrue(validation_result.is_valid, 
                       f"Validation failed: {validation_result.error_message}")

    def test_component_detection(self):
        """Test component detection in scene"""
        result = self.scene_handler.process_scene(
            str(self.test_scene_path),
            'living_room'
        )
        
        self.assertTrue(result.success, f"Processing failed: {result.message}")
        self.assertIsNotNone(result.components)
        self.assertGreater(len(result.components), 0)

    def test_database_integration(self):
        """Test database integration with scene processing"""
        result = self.scene_handler.process_scene(
            str(self.test_scene_path),
            'living_room'
        )
        
        self.assertTrue(result.success, f"Processing failed: {result.message}")
        
        # Verify room scene was created
        room_scene = self.db.query(RoomScene).get(result.room_scene_id)
        self.assertIsNotNone(room_scene)
        self.assertEqual(room_scene.category, 'living_room')
        
        # Verify components were created
        components = self.db.query(Component).filter_by(
            room_scene_id=result.room_scene_id
        ).all()
        self.assertGreater(len(components), 0)

    def test_component_processing(self):
        """Test individual component processing"""
        result = self.scene_handler.process_scene(
            str(self.test_scene_path),
            'living_room'
        )
        
        self.assertTrue(result.success, f"Processing failed: {result.message}")
        self.assertIsNotNone(result.components)
        
        # Check first component
        if result.components:
            component = result.components[0]
            print(f"\nComponent info: {component}")
            
            self.assertIn('component_id', component)
            self.assertIn('bounds', component)
            self.assertIn('path', component)
            
            # Verify component file exists
            self.assertTrue(os.path.exists(component['path']), 
                          f"Component file not found at {component['path']}")

    def test_error_handling(self):
        """Test error handling for invalid scenes"""
        # Test with non-existent file
        result = self.scene_handler.process_scene(
            'nonexistent.jpg',
            'living_room'
        )
        
        self.assertFalse(result.success)
        self.assertIsNotNone(result.message)
        
        # Verify error was logged
        log_files = list(Path(self.error_logger.log_dir).glob('*.log'))
        self.assertTrue(len(log_files) > 0)

    def test_spatial_data_extraction(self):
        """Test spatial data extraction from components"""
        result = self.scene_handler.process_scene(
            str(self.test_scene_path),
            'living_room'
        )
        
        self.assertTrue(result.success, f"Processing failed: {result.message}")
        
        # Get components from database
        components = self.db.query(Component).filter_by(
            room_scene_id=result.room_scene_id
        ).all()
        
        for component in components:
            position_data = component.position_data
            self.assertIsNotNone(position_data)
            self.assertIn('bounds', position_data)
            self.assertIn('center', position_data)
            self.assertIn('size', position_data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
