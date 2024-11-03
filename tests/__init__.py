import unittest
from flask import Flask
from app import create_app
from app.database import db_manager, db
from app.models import RoomScene, Component, ComponentStatus
from app.config import Config

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        # Configure test app
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['SERVER_NAME'] = 'localhost.localdomain'
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Initialize database
        db_manager.init_db()
        self.db = db_manager.get_session()
    
    def tearDown(self):
        if self.db:
            # Clear test database
            self.db.rollback()
            self.db.close()
            
            # Drop all tables within app context
            with self.app.app_context():
                db.drop_all()
            
            db_manager.cleanup_session()
        
        self.app_context.pop()

    def create_test_scene(self, **kwargs):
        """Helper to create a test scene"""
        scene_data = {
            'name': 'Test Scene',
            'category': 'kitchen',
            'file_path': 'test/path.jpg',
            **kwargs
        }
        scene = RoomScene(**scene_data)
        self.db.add(scene)
        self.db.commit()
        return scene

    def create_test_component(self, scene_id, **kwargs):
        """Helper to create a test component"""
        component_data = {
            'room_scene_id': scene_id,
            'name': 'Test Component',
            'component_type': 'appliance',
            'file_path': 'test/component.jpg',
            'status': ComponentStatus.PENDING,
            **kwargs
        }
        component = Component(**component_data)
        self.db.add(component)
        self.db.commit()
        return component