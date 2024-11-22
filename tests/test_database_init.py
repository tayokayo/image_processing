import unittest
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from app import create_app
from app.extensions import db
from app.database import db_session
from app.models import RoomScene, Component, ProcessedResult

class TestDatabaseInitialization(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create test app
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'app_context'):
            self.app_context.pop()

    def test_database_setup(self):
        """Verify database initialization and table creation"""
        self.logger.info("\nTesting database initialization...")
        
        try:
            with db_session() as session:
                # Drop any existing tables
                self.logger.info("Dropping existing tables...")
                db.drop_all()
                
                # Create tables
                self.logger.info("Creating tables...")
                db.create_all()
                
                # Verify PostgreSQL-specific features
                self.logger.info("Verifying PostgreSQL features...")
                session.execute(text("SELECT version()")).scalar()
                
                # Create test image data
                test_image = b'test image data'
                
                self.logger.info("\nTesting table creation:")
                # Create test scene with image data
                scene = RoomScene(
                    name='Test Scene',
                    category='living_room',
                    image_data=test_image,
                    scene_metadata={'test': 'data'},
                    processed=False
                )
                session.add(scene)
                session.flush()
                
                # Create test component
                component = Component(
                    room_scene_id=scene.id,
                    name='Test Component',
                    component_type='furniture',
                    position_data={'bounds': [0, 0, 100, 100]},
                    status='PENDING'
                )
                session.add(component)
                session.commit()
                
                # Verify records
                saved_scene = session.execute(text("""
                    SELECT id, name, category, scene_metadata, processed
                    FROM room_scenes
                    WHERE id = :scene_id
                """), {'scene_id': scene.id}).first()
                
                saved_component = session.execute(text("""
                    SELECT id, room_scene_id, name, component_type, status
                    FROM components
                    WHERE id = :comp_id
                """), {'comp_id': component.id}).first()
                
                # Verify scene data
                assert saved_scene is not None
                assert saved_scene.name == 'Test Scene'
                assert saved_scene.processed is False
                assert isinstance(saved_scene.scene_metadata, dict)
                
                # Verify component data
                assert saved_component is not None
                assert saved_component.room_scene_id == scene.id
                assert saved_component.status == 'PENDING'
                
                self.logger.info("✓ All database tests passed")
                
        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")
            raise

if __name__ == '__main__':
    unittest.main()