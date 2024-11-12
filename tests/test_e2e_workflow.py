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

class TestEndToEndWorkflow(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # 1. Configure logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Setting up test environment...")

        # 2. Create app and use app context
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

        # 3. Initialize database
        db.create_all()

        # 4. Setup test directories
        self._setup_test_directories()

        # 5. Clean existing test data
        with db_session() as session:
            session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            session.execute(text("""
                TRUNCATE room_scenes, components 
                RESTART IDENTITY CASCADE
            """))
            session.commit()

        # 6. Initialize application components
        self.client = self.app.test_client()
        self._setup_sam_processor()
        self._verify_database_connection()

        self.logger.info("✓ Test environment setup completed")

    def _setup_test_directories(self):
        """Setup test directories"""
        self.test_dir = Path('test_storage')
        self.scenes_dir = self.test_dir / 'scenes'
        self.components_dir = self.test_dir / 'components'
        self.temp_dir = self.test_dir / 'temp'
        
        for dir_path in [self.scenes_dir, self.components_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.app.config['UPLOAD_FOLDER'] = str(self.temp_dir)

    def _setup_sam_processor(self):
        """Initialize SAM processor"""
        from app.processing.sam_processor import SAMProcessor
        self.app.sam_processor = SAMProcessor(
            self.app.config.get('SAM_MODEL_PATH', 'test_model_path')
        )

    def _verify_database_connection(self):
        """Verify database connection with test record"""
        try:
            with db_session() as session:
                test_scene = RoomScene(
                    name='Test Scene',
                    category='living_room',
                    file_path='test/path.jpg'
                )
                session.add(test_scene)
                session.commit()
                
                verify_scene = session.query(RoomScene).first()
                if not verify_scene:
                    raise Exception("Database verification failed")
                
                session.delete(verify_scene)
                session.commit()
        except Exception as e:
            raise Exception(f"Database setup failed: {str(e)}")

    def tearDown(self):
        """Clean up test environment"""
        self.logger.info("Cleaning up test environment...")

        try:
            with db_session() as session:
                session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
                session.execute(text("""
                    TRUNCATE room_scenes, components 
                    RESTART IDENTITY CASCADE
                """))
            self.logger.info("✓ Database tables cleaned")
        except SQLAlchemyError as e:
            self.logger.error(f"Database cleanup error: {str(e)}")

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

        self.app_context.pop()
        self.logger.info("✓ Test environment cleanup completed")

    # Image creation methods remain the same
    def _create_blurry_image(self):
        """Reference original implementation"""
        startLine: 143
        endLine: 156

    def _create_quality_image(self):
        """Reference original implementation"""
        startLine: 158
        endLine: 180

    def test_complete_workflow(self):
        """Reference original implementation with updated session management"""
        startLine: 143
        endLine: 315

    def verify_db_state(self, point_name: str):
        """Helper to verify database state at key points"""
        self.logger.info(f"\nDatabase state at: {point_name}")
        try:
            with db_session() as session:
                # Check scenes with explicit column selection
                scenes = session.execute(text("""
                    SELECT id, name, category, 
                           created_at, updated_at
                    FROM room_scenes
                """)).fetchall()
                self.logger.info(f"Room Scenes ({len(scenes)}):")
                for scene in scenes:
                    self.logger.info(
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
                self.logger.info(f"Components ({len(components)}):")
                for comp in components:
                    self.logger.info(
                        f"  - ID: {comp.id}, Scene: {comp.room_scene_id}, "
                        f"Status: {comp.status}"
                    )
        except Exception as e:
            self.logger.error(f"Failed to verify DB state: {e}")

    def verify_transaction(self, operation: str):
        """Helper to verify transaction state"""
        try:
            with db_session() as session:
                result = session.execute(text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                    AND query NOT LIKE '%pg_stat_activity%'
                """)).scalar()
                
                self.logger.info(f"\nTransaction check ({operation}):")
                self.logger.info(f"- Active transactions: {result}")
                self.logger.info(f"- Session state: {session.is_active}")
        except Exception as e:
            self.logger.error(f"Transaction verification failed: {e}")

if __name__ == '__main__':
    unittest.main()