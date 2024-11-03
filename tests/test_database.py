import unittest
import os
from pathlib import Path
import json
import shutil
from datetime import datetime
from app import create_app
from app.database import db_manager
from app.models import RoomScene, Component, ProcessedResult
from app.processing.file_manager import FileManager
from app.config import Config

class TestDatabaseAndStorage(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Configure test app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SERVER_NAME'] = 'localhost.localdomain'
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create test directories
        self.test_base_dir = Path('test_storage')
        self.file_manager = FileManager(self.test_base_dir)
        
        # Initialize database
        db_manager.init_db()
        self.db = db_manager.get_session()
        
        # Create test file
        self.test_file = self.test_base_dir / 'test_scene.jpg'
        self._create_test_file()

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up database
        self.db.close()
        db_manager.cleanup_session()
        
        # Clean up test files
        if self.test_base_dir.exists():
            shutil.rmtree(self.test_base_dir)
            
        # Remove Flask context
        self.app_context.pop()

    def _create_test_file(self):
        """Create a test file"""
        self.test_base_dir.mkdir(parents=True, exist_ok=True)
        with open(self.test_file, 'wb') as f:
            f.write(b'test content')

    def test_database_initialization(self):
        """Test database setup"""
        # Add test room scene
        room_scene = RoomScene(
            name='Test Room',
            category='living_room',
            file_path=str(self.test_file),
            scene_metadata={'size': 'large'}  # Changed from metadata to scene_metadata
        )
        self.db.add(room_scene)
        self.db.commit()
        
        # Verify room scene was saved
        saved_scene = self.db.query(RoomScene).first()
        self.assertIsNotNone(saved_scene)
        self.assertEqual(saved_scene.name, 'Test Room')

    def test_component_relationship(self):
        """Test relationship between room scene and components"""
        # Create room scene
        room_scene = RoomScene(
            name='Test Room',
            category='living_room',
            file_path=str(self.test_file)
        )
        self.db.add(room_scene)
        self.db.commit()
        
        # Add component
        component = Component(
            room_scene_id=room_scene.id,
            name='Test Sofa',
            component_type='furniture',
            file_path=str(self.test_file),
            position_data={'x': 0, 'y': 0}
        )
        self.db.add(component)
        self.db.commit()
        
        # Verify relationship
        self.assertEqual(len(room_scene.components), 1)
        self.assertEqual(room_scene.components[0].name, 'Test Sofa')

    def test_file_manager(self):
        """Test file management operations"""
        # Test scene saving
        with open(self.test_file, 'rb') as f:
            path, error = self.file_manager.save_scene(f, 'test_scene.jpg')
        
        self.assertIsNotNone(path)
        self.assertIsNone(error)
        self.assertTrue(os.path.exists(path))
        
        # Test metadata saving
        metadata = {'test': 'data'}
        meta_path, error = self.file_manager.save_metadata(
            metadata, 'test_metadata'
        )
        
        self.assertIsNotNone(meta_path)
        self.assertIsNone(error)
        
        # Verify metadata
        with open(meta_path, 'r') as f:
            saved_metadata = json.load(f)
        self.assertEqual(saved_metadata, metadata)

    def test_processed_result(self):
        """Test processed result storage"""
        # Create component
        room_scene = RoomScene(
            name='Test Room',
            category='living_room',
            file_path=str(self.test_file)
        )
        self.db.add(room_scene)
        self.db.commit()
        
        component = Component(
            room_scene_id=room_scene.id,
            name='Test Component',
            component_type='furniture',
            file_path=str(self.test_file)
        )
        self.db.add(component)
        self.db.commit()
        
        # Add processed result
        result = ProcessedResult(
            component_id=component.id,
            original_path=str(self.test_file),
            processed_path=str(self.test_file),
            processing_metadata={'status': 'success'}
        )
        self.db.add(result)
        self.db.commit()
        
        # Verify result
        saved_result = self.db.query(ProcessedResult).first()
        self.assertIsNotNone(saved_result)
        self.assertEqual(
            saved_result.processing_metadata['status'], 
            'success'
        )

if __name__ == '__main__':
    unittest.main()