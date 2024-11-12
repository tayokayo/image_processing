import unittest
from flask import Flask
from sqlalchemy import text
from app import create_app
from app.database import db, db_session
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
        db.create_all()
    
    def tearDown(self):
        # Clean up database
        with db_session() as session:
            try:
                session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
                session.execute(text("""
                    TRUNCATE room_scenes, components, processed_results 
                    RESTART IDENTITY CASCADE
                """))
            except Exception as e:
                print(f"Cleanup error: {e}")
        
        # Drop all tables within app context
        with self.app.app_context():
            db.drop_all()
        
        self.app_context.pop()

    def create_test_scene(self, **kwargs):
        """Helper to create a test scene"""
        scene_data = {
            'name': 'Test Scene',
            'category': 'kitchen',
            'file_path': 'test/path.jpg',
            **kwargs
        }
        with db_session() as session:
            scene = RoomScene(**scene_data)
            session.add(scene)
            session.commit()
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
        with db_session() as session:
            component = Component(**component_data)
            session.add(component)
            session.commit()
            return component