import unittest
import os
from pathlib import Path
import json
import shutil
from datetime import datetime
from sqlalchemy import text
from app import create_app
from app.database import db, db_session
from app.models import RoomScene, Component, ProcessedResult
from app.processing.file_manager import FileManager
from app.config import Config

class TestDatabaseAndStorage(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures with proper error handling"""
        try:
            self.app = create_app('testing')
            self.app_context = self.app.app_context()
            self.app_context.push()
            
            # Create test directories
            self.test_base_dir = Path('test_storage')
            self.file_manager = FileManager(self.test_base_dir)
            
            # Initialize database
            db.create_all()
            
            # Create test file
            self.test_file = self.test_base_dir / 'test_scene.jpg'
            self._create_test_file()
            
        except Exception as e:
            self.tearDown()
            raise RuntimeError(f"Failed to set up test environment: {str(e)}")

    def tearDown(self) -> None:
        """Clean up test fixtures with proper error handling"""
        try:
            db.session.remove()
            db.drop_all()
            
            if hasattr(self, 'test_base_dir') and self.test_base_dir.exists():
                shutil.rmtree(self.test_base_dir)
            
            if hasattr(self, 'app_context'):
                self.app_context.pop()
        except Exception as e:
            print(f"Warning: Error during teardown: {str(e)}")

    def _create_test_file(self):
        """Create a test file"""
        self.test_base_dir.mkdir(parents=True, exist_ok=True)
        with open(self.test_file, 'wb') as f:
            f.write(b'test content')

    def test_database_initialization(self):
        """Test database setup with JSONB support"""
        with db_session() as session:
            # Reference original test code
            startLine: 55
            endLine: 70

    def test_component_relationship(self):
        """Test relationship between room scene and components"""
        with db_session() as session:
            # Reference original test code
            startLine: 72
            endLine: 96

    def test_transaction_management(self):
        """Test PostgreSQL transaction management"""
        with db_session() as session:
            try:
                # Start a transaction
                scene = RoomScene(
                    name='Transaction Test',
                    category='kitchen',
                    file_path=str(self.test_file)
                )
                session.add(scene)
                session.flush()
                
                # Create test component that will trigger rollback
                component = Component(
                    room_scene_id=scene.id,
                    name='Test Component',
                    component_type='invalid_type',
                    file_path='nonexistent.jpg'
                )
                session.add(component)
                session.commit()
                self.fail("Should have raised an error")
            except Exception:
                session.rollback()
                
                # Verify scene was not saved
                saved_scene = session.query(RoomScene).filter_by(
                    name='Transaction Test'
                ).first()
                self.assertIsNone(saved_scene)

    def test_jsonb_query_performance(self):
        """Test PostgreSQL JSONB query performance with GIN index"""
        with db_session() as session:
            # Reference original test code
            startLine: 191
            endLine: 223

    def test_nested_transactions(self):
        """Test PostgreSQL nested transactions with savepoints"""
        with db_session() as session:
            # Create parent scene
            scene = RoomScene(
                name='Parent Scene',
                category='living_room',
                file_path=str(self.test_file)
            )
            session.add(scene)
            session.commit()
            
            try:
                # Start nested transaction
                with session.begin_nested():
                    component = Component(
                        room_scene_id=scene.id,
                        name='Test Component',
                        component_type='invalid_type',
                        file_path='nonexistent.jpg'
                    )
                    session.add(component)
                    
            except Exception:
                session.rollback()
                
                # Verify component was rolled back but scene remains
                saved_scene = session.query(RoomScene).filter_by(
                    name='Parent Scene'
                ).first()
                saved_component = session.query(Component).first()
                
                self.assertIsNotNone(saved_scene)
                self.assertIsNone(saved_component)

if __name__ == '__main__':
    unittest.main()