import unittest
import io
import os
import shutil
from pathlib import Path
import json
import cv2
from PIL import Image
import numpy as np
from flask import url_for
from app.extensions import db
from app.database import db_session
from app.models import RoomScene, Component, ComponentStatus
from app import create_app
from app.processing.scene_handler import SceneHandler
from app.processing.error_logger import ErrorLogger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging
from app.processing.sam_processor import SAMProcessor

class TestEndToEndWorkflow(unittest.TestCase):
    def _create_blurry_image(self):
        """Create a blurry test image"""
        img = np.ones((300, 400, 3), np.uint8) * 255
        blur = cv2.GaussianBlur(img, (51, 51), 0)
        _, buffer = cv2.imencode('.jpg', blur)
        return buffer.tobytes()

    def _create_quality_image(self):
        """Create a high-quality test image"""
        img = np.ones((300, 400, 3), np.uint8) * 255
        img[:, :, 0] = 0
        img[:, :, 1] = 255
        img[:, :, 2] = 0
        _, buffer = cv2.imencode('.jpg', img)
        return buffer.tobytes()

    def setUp(self):
        """Set up test environment for production database"""
        try:
            # Configure logging
            logging.basicConfig(level=logging.INFO)
            
            # Load environment variables for database connection
            db_user = os.getenv('DB_USER')
            db_password = os.getenv('DB_PASSWORD')
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT')
            db_name = os.getenv('DB_NAME')
            sam_model_path = os.getenv('SAM_MODEL_PATH')
            
            if not all([db_user, db_password, db_host, db_port, db_name]):
                raise ValueError("Missing required database environment variables")
            
            # Initialize app context with production database config
            self.app = create_app('production')
            self.app.config.update({
                'SERVER_NAME': 'localhost.localdomain',
                'PREFERRED_URL_SCHEME': 'http',
                'APPLICATION_ROOT': '/',
                'SQLALCHEMY_DATABASE_URI': f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
            })
            self.app_context = self.app.app_context()
            self.app_context.push()
            
            # Initialize components
            self.error_logger = ErrorLogger()
            self.sam_processor = SAMProcessor(model_path=sam_model_path)
            self.scene_handler = SceneHandler(
                sam_processor=self.sam_processor,
                error_logger=self.error_logger
            )
            
            # Register scene handler with app
            self.app.scene_handler = self.scene_handler
            
        except Exception as e:
            self.tearDown()
            raise RuntimeError(f"Failed to set up test environment: {str(e)}")

    def tearDown(self):
        """Clean up test environment"""
        try:
            # Only remove session, don't truncate production tables
            db.session.remove()
            
            if hasattr(self, 'app_context'):
                self.app_context.pop()
                
        except Exception as e:
            print(f"Warning: Error during tearDown: {str(e)}")

    def test_complete_workflow(self):
        """Test end-to-end workflow with proper context management"""
        client = self.app.test_client()

        try:
            # Create test images
            blurry_image = self._create_blurry_image()
            quality_image = self._create_quality_image()

            # Test blurry image upload
            with db_session() as session:
                # Create scene record with blurry image data
                blurry_scene = RoomScene(
                    name='blurry_test_scene',
                    category='living_room',
                    image_data=blurry_image,
                    metadata={'quality': 'low'}
                )
                session.add(blurry_scene)
                session.flush()

                # Process blurry scene
                response = client.post(
                    url_for('admin.process_scene'),
                    json={'scene_id': blurry_scene.id}
                )
                assert response.status_code in [200, 400]

                # Verify scene was processed
                processed_scene = session.execute(
                    text("SELECT * FROM room_scenes WHERE id = :id"),
                    {"id": blurry_scene.id}
                ).first()
                assert processed_scene is not None

            # Test quality image upload
            with db_session() as session:
                # Create scene record with quality image data
                quality_scene = RoomScene(
                    name='quality_test_scene',
                    category='living_room',
                    image_data=quality_image,
                    metadata={'quality': 'high'}
                )
                session.add(quality_scene)
                session.flush()

                # Process quality scene
                response = client.post(
                    url_for('admin.process_scene'),
                    json={'scene_id': quality_scene.id}
                )
                assert response.status_code in [200, 400]

                # Wait for processing completion
                scene = session.execute(
                    text("""
                        SELECT * FROM room_scenes 
                        WHERE id = :id AND processed = true
                    """),
                    {"id": quality_scene.id}
                ).first()
                
                while not scene:
                    scene = session.execute(
                        text("""
                            SELECT * FROM room_scenes 
                            WHERE id = :id AND processed = true
                        """),
                        {"id": quality_scene.id}
                    ).first()

                # Verify components were created
                components = session.execute(
                    text("""
                        SELECT * FROM components 
                        WHERE room_scene_id = :scene_id 
                        AND status = 'PENDING'
                    """),
                    {"scene_id": quality_scene.id}
                ).fetchall()
                
                assert len(components) > 0

        finally:
            self.app_context.pop()

    def verify_db_state(self, point_name: str):
        """Helper to verify database state at key points"""
        logger = logging.getLogger(__name__)
        logger.info(f"\nDatabase state at: {point_name}")
        try:
            with db_session() as session:
                # Check scenes with explicit column selection
                scenes = session.execute(text("""
                    SELECT id, name, category, 
                           created_at, updated_at
                    FROM room_scenes
                """)).fetchall()
                logger.info(f"Room Scenes ({len(scenes)}):")
                for scene in scenes:
                    logger.info(
                        f"  - ID: {scene.id}, Name: {scene.name}, "
                        f"Category: {scene.category}"
                    )

                # Check components with explicit column selection
                components = session.execute(text("""
                    SELECT id, room_scene_id, status, 
                           component_type, created_at
                    FROM components
                    ORDER BY created_at DESC
                """)).fetchall()
                logger.info(f"Components ({len(components)}):")
                for comp in components:
                    logger.info(
                        f"  - ID: {comp.id}, Scene: {comp.room_scene_id}, "
                        f"Status: {comp.status}"
                    )
        except Exception as e:
            logger.error(f"Failed to verify DB state: {e}")

    def verify_transaction(self, operation: str):
        """Helper to verify transaction state"""
        logger = logging.getLogger(__name__)
        try:
            with db_session() as session:
                result = session.execute(text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                    AND query NOT LIKE '%pg_stat_activity%'
                """)).scalar()
                
                logger.info(f"\nTransaction check ({operation}):")
                logger.info(f"- Active transactions: {result}")
                logger.info(f"- Session state: {session.is_active}")
        except Exception as e:
            logger.error(f"Transaction verification failed: {e}")

if __name__ == '__main__':
    unittest.main()