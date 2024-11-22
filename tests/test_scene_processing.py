import unittest
import logging
import numpy as np
import cv2
from datetime import datetime, timedelta
from sqlalchemy.exc import DatabaseError
from sqlalchemy import text
from app.processing.scene_handler import SceneHandler
from app.processing.scene_validator import SceneValidator, ValidationResult
from app.processing.sam_processor import SAMProcessor
from app.processing.error_logger import ErrorLogger
from app.database import db_session
from app.models import RoomScene, Component, ComponentStatus

class TestSceneProcessing(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        logging.basicConfig(level=logging.INFO)
        
        # Initialize components
        self.error_logger = ErrorLogger()
        self.sam_processor = SAMProcessor()
        self.scene_handler = SceneHandler(
            sam_processor=self.sam_processor,
            error_logger=self.error_logger
        )
        
        # Create test image data
        img = np.ones((300, 400, 3), np.uint8) * 255
        _, buffer = cv2.imencode('.jpg', img)
        self.test_image_data = buffer.tobytes()

    def test_process_scene_success(self):
        """Test successful scene processing flow"""
        with db_session() as session:
            # Create test scene with image data
            scene = RoomScene(
                name='test_scene',
                category='living_room',
                image_data=self.test_image_data,
                scene_metadata={'quality': 'high'}
            )
            session.add(scene)
            session.commit()

            # Process scene
            result = self.scene_handler.process_scene(scene.id)

            # Verify success
            self.assertTrue(result.success)
            self.assertEqual(result.room_scene_id, scene.id)
            self.assertIsNotNone(result.components)
            self.assertIsNotNone(result.statistics)

            # Verify scene was updated
            processed_scene = session.get(RoomScene, scene.id)
            self.assertTrue(processed_scene.processed)
            self.assertIsNotNone(processed_scene.updated_at)

    def test_process_scene_missing_image(self):
        """Test scene processing with missing image data"""
        with db_session() as session:
            # Create scene without image data
            scene = RoomScene(
                name='test_scene',
                category='living_room'
            )
            session.add(scene)
            session.commit()

            # Attempt to process scene
            result = self.scene_handler.process_scene(scene.id)

            # Verify failure
            self.assertFalse(result.success)
            self.assertEqual(
                result.error_details.get('error_type'),
                'invalid_scene'
            )

    def test_process_scene_transaction_handling(self):
        """Test transaction handling during scene processing"""
        with db_session() as session:
            # Create test scene
            scene = RoomScene(
                name='test_scene',
                category='living_room',
                image_data=self.test_image_data
            )
            session.add(scene)
            session.commit()

            # Mock SAM processor to raise exception
            def mock_detect(*args):
                raise ValueError("Simulated detection error")
            
            self.scene_handler.sam_processor.detect_components = mock_detect

            # Process scene
            result = self.scene_handler.process_scene(scene.id)

            # Verify failure but scene remains
            self.assertFalse(result.success)
            self.assertEqual(result.room_scene_id, scene.id)
            self.assertEqual(
                result.error_details.get('component_error'),
                'Simulated detection error'
            )

            # Verify scene still exists but not marked as processed
            scene = session.get(RoomScene, scene.id)
            self.assertIsNotNone(scene)
            self.assertFalse(scene.processed)

    def tearDown(self):
        """Clean up test environment"""
        with db_session() as session:
            session.execute(text("TRUNCATE room_scenes, components RESTART IDENTITY CASCADE"))

class TestSceneStatistics(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
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
                image_data=self.test_image_data,
                scene_metadata={'quality': 'high'}
            )
            session.add(self.scene)
            session.commit()
            
            # Add test components with different statuses and scores
            self.components = [
                Component(
                    room_scene_id=self.scene.id,
                    name='Component 1',
                    component_type='furniture',
                    status=ComponentStatus.ACCEPTED,
                    confidence_score=0.85,
                    created_at=datetime.utcnow() - timedelta(hours=2),
                    review_timestamp=datetime.utcnow() - timedelta(hours=1)
                ),
                Component(
                    room_scene_id=self.scene.id,
                    name='Component 2',
                    component_type='decor',
                    status=ComponentStatus.REJECTED,
                    confidence_score=0.45,
                    created_at=datetime.utcnow() - timedelta(hours=1),
                    review_timestamp=datetime.utcnow()
                )
            ]
            session.add_all(self.components)
            session.commit()

    def test_statistics_calculation(self):
        """Test scene statistics calculation"""
        with db_session() as session:
            stats = self.scene_handler._get_scene_statistics(self.scene)
            
            self.assertEqual(stats['total_components'], 2)
            self.assertEqual(stats['accepted_components'], 1)
            self.assertEqual(stats['rejected_components'], 1)
            self.assertEqual(stats['pending_components'], 0)

    def test_statistics_update(self):
        """Test statistics update after component changes"""
        with db_session() as session:
            # Add new pending component
            new_component = Component(
                room_scene_id=self.scene.id,
                name='New Component',
                component_type='lighting',
                status=ComponentStatus.PENDING,
                confidence_score=0.65
            )
            session.add(new_component)
            session.commit()

            # Verify updated statistics
            stats = self.scene_handler._get_scene_statistics(self.scene)
            self.assertEqual(stats['total_components'], 3)
            self.assertEqual(stats['pending_components'], 1)

    def test_transaction_handling(self):
        """Test transaction handling during statistics refresh"""
        with db_session() as session:
            # Create a new component that will trigger a transaction
            new_component = Component(
                room_scene_id=self.scene.id,
                name='Transaction Test Component',
                component_type='furniture',
                status=ComponentStatus.PENDING,
                confidence_score=0.75,
                created_at=datetime.utcnow()
            )
            session.add(new_component)
            session.commit()
            
            try:
                # Simulate a transaction error
                session.execute(text("SELECT * FROM nonexistent_table"))
                self.fail("Should have raised an error")
            except DatabaseError as e:
                # Verify transaction was rolled back
                self.assertIn("relation \"nonexistent_table\" does not exist", str(e))
                
                # Verify statistics are still accessible
                stats = self.scene_handler._get_scene_statistics(self.scene)
                self.assertIsNotNone(stats)
                self.assertEqual(stats['total_components'], 3)
                
                # Verify component still exists
                component = session.query(Component).filter_by(
                    name='Transaction Test Component'
                ).first()
                self.assertIsNotNone(component)

    def tearDown(self):
        """Clean up test environment"""
        with db_session() as session:
            session.execute(text("TRUNCATE room_scenes, components RESTART IDENTITY CASCADE"))

if __name__ == '__main__':
    unittest.main(verbosity=2)