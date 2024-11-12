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
                
                self.logger.info("\nTesting table creation:")
                # Create test records with proper transaction handling
                scene = RoomScene(
                    name='Test Scene',
                    category='living_room',
                    file_path='test/path.jpg',
                    scene_metadata={'test': 'data'}  # Testing JSONB
                )
                session.add(scene)
                session.flush()  # Get ID without committing
                
                component = Component(
                    room_scene_id=scene.id,
                    name='Test Component',
                    component_type='furniture',
                    file_path='test/component.jpg',
                    status='PENDING'  # Testing enum
                )
                session.add(component)
                session.flush()
                
                result = ProcessedResult(
                    component_id=component.id,
                    original_path='test/original.jpg',
                    processed_path='test/processed.jpg',
                    metadata={'processing': 'complete'}  # Testing JSONB
                )
                session.add(result)
                session.commit()
                self.logger.info("✓ Created all test records")
                
                # Verify records with explicit column selection
                self.logger.info("\nVerifying records:")
                scenes = session.execute(text("""
                    SELECT id, name, category, scene_metadata
                    FROM room_scenes
                    WHERE id = :scene_id
                """), {'scene_id': scene.id}).first()
                
                components = session.execute(text("""
                    SELECT id, room_scene_id, status, component_type
                    FROM components
                    WHERE id = :comp_id
                """), {'comp_id': component.id}).first()
                
                results = session.execute(text("""
                    SELECT id, component_id, metadata
                    FROM processed_results
                    WHERE id = :result_id
                """), {'result_id': result.id}).first()
                
                # Verify record counts
                self.assertIsNotNone(scenes, "Scene should exist")
                self.assertIsNotNone(components, "Component should exist")
                self.assertIsNotNone(results, "ProcessedResult should exist")
                
                # Verify PostgreSQL-specific features
                self.assertIsInstance(scenes.scene_metadata, dict, "JSONB should be converted to dict")
                self.assertEqual(components.status, 'PENDING', "Enum should work correctly")
                
                self.logger.info("✓ All records verified")
                
        except Exception as e:
            self.logger.error(f"\nError during database testing: {str(e)}")
            raise
        finally:
            # Clean up
            with db_session() as session:
                session.execute(text("TRUNCATE room_scenes, components, processed_results RESTART IDENTITY CASCADE"))
            self.logger.info("\nDatabase cleanup completed")

if __name__ == '__main__':
    unittest.main()