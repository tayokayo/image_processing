import unittest
import os
import shutil
import logging
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
from datetime import datetime, timedelta

from sqlalchemy.exc import DatabaseError
from sqlalchemy import text
from app.processing.scene_handler import SceneHandler
from app.processing.scene_validator import SceneValidator, ValidationResult
from app.processing.sam_processor import SAMProcessor
from app.processing.error_logger import ErrorLogger
from app.database import db, db_session
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

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up database
        with db_session() as session:
            session.execute(text("TRUNCATE room_scenes, components RESTART IDENTITY CASCADE"))
        
        # Clean up test directories
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _create_test_scene(self):
        """Reference original implementation"""
        startLine: 67
        endLine: 115

    def test_scene_validation(self):
        """Reference original implementation"""
        startLine: 117
        endLine: 128

    def test_component_detection(self):
        """Reference original implementation"""
        startLine: 130
        endLine: 139

class TestSceneStatistics(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Initialize components
        self.error_logger = ErrorLogger()
        self.sam_processor = SAMProcessor()
        self.scene_handler = SceneHandler(
            sam_processor=self.sam_processor,
            error_logger=self.error_logger
        )
        
        # Create test scene with components
        with db_session() as session:
            self.scene = RoomScene(
                name='Test Scene',
                category='living_room',
                file_path='test/path.jpg'
            )
            session.add(self.scene)
            session.commit()
            
            # Add test components with different statuses and scores
            self.components = [
                Component(
                    room_scene_id=self.scene.id,
                    name='Component 1',
                    component_type='furniture',
                    status='ACCEPTED',
                    confidence_score=0.85,
                    created_at=datetime.now() - timedelta(hours=2),
                    review_timestamp=datetime.now() - timedelta(hours=1)
                ),
                Component(
                    room_scene_id=self.scene.id,
                    name='Component 2',
                    component_type='decor',
                    status='REJECTED',
                    confidence_score=0.45,
                    created_at=datetime.now() - timedelta(hours=1),
                    review_timestamp=datetime.now()
                )
            ]
            session.add_all(self.components)
            session.commit()

    def tearDown(self):
        """Clean up test environment"""
        with db_session() as session:
            session.execute(text("TRUNCATE room_scenes, components RESTART IDENTITY CASCADE"))

    def test_refresh_statistics(self):
        """Reference original implementation"""
        startLine: 282
        endLine: 301

    def test_cached_statistics(self):
        """Reference original implementation"""
        startLine: 303
        endLine: 324

    def test_statistics_error_handling(self):
        """Reference original implementation"""
        startLine: 326
        endLine: 336

    def test_transaction_handling(self):
        """Test transaction handling during statistics refresh"""
        with db_session() as session:
            # Create a new component that will trigger a transaction
            new_component = Component(
                room_scene_id=self.scene.id,
                name='Transaction Test Component',
                component_type='furniture',
                status='PENDING',
                confidence_score=0.75,
                created_at=datetime.now()
            )
            session.add(new_component)
            session.commit()
            
            try:
                # Simulate a transaction error by passing invalid SQL
                session.execute(text("SELECT * FROM nonexistent_table"))
                self.fail("Should have raised an error")
            except DatabaseError as e:
                # Verify transaction was rolled back
                self.assertIn("relation \"nonexistent_table\" does not exist", str(e))
                
                # Verify statistics are still accessible
                stats = self.scene_handler.refresh_statistics(self.scene.id)
                self.assertIsNotNone(stats)
                self.assertEqual(stats['total_components'], 3)  # Including new component
                
                # Verify component still exists
                component = session.query(Component).filter_by(
                    name='Transaction Test Component'
                ).first()
                self.assertIsNotNone(component)

if __name__ == '__main__':
    unittest.main(verbosity=2)