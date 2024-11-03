import unittest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app import create_app
from app.database import db
from app.models import RoomScene, Component, ProcessedResult

class TestDatabaseInitialization(unittest.TestCase):
    def test_database_setup(self):
        """Verify database initialization and table creation"""
        print("\nTesting database initialization...")
        
        # Create test app
        app = create_app('testing')
        
        with app.app_context():
            # Get database URL
            print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            try:
                # Drop any existing tables
                print("Dropping existing tables...")
                db.drop_all()
                
                # Create tables
                print("Creating tables...")
                db.create_all()
                
                print("\nTesting table creation:")
                # Try creating test records
                scene = RoomScene(
                    name='Test Scene',
                    category='living_room',
                    file_path='test/path.jpg'
                )
                db.session.add(scene)
                db.session.commit()
                print("✓ Created RoomScene")
                
                component = Component(
                    room_scene_id=scene.id,
                    name='Test Component',
                    component_type='furniture',
                    file_path='test/component.jpg'
                )
                db.session.add(component)
                db.session.commit()
                print("✓ Created Component")
                
                result = ProcessedResult(
                    component_id=component.id,
                    original_path='test/original.jpg',
                    processed_path='test/processed.jpg'
                )
                db.session.add(result)
                db.session.commit()
                print("✓ Created ProcessedResult")
                
                # Verify records
                print("\nVerifying records:")
                scenes = RoomScene.query.all()
                components = Component.query.all()
                results = ProcessedResult.query.all()
                
                self.assertEqual(len(scenes), 1, "Should have one scene")
                self.assertEqual(len(components), 1, "Should have one component")
                self.assertEqual(len(results), 1, "Should have one result")
                
                print("✓ All records verified")
                
                # Clean up
                db.session.remove()
                db.drop_all()
                print("\nDatabase cleanup completed")
                
            except Exception as e:
                print(f"\nError during database testing: {str(e)}")
                db.session.rollback()
                raise

if __name__ == '__main__':
    unittest.main()