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
from app.database import db
from app.models import RoomScene, Component, ComponentStatus
from app import create_app
from app.processing.scene_handler import SceneHandler
from app.processing.error_logger import ErrorLogger

class TestEndToEndWorkflow(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        print("\nSetting up test environment...")
        
        # Create test app with in-memory SQLite
        self.app = create_app('testing')
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        # Initialize app context first
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Initialize database tables
        db.create_all()
        
        # Initialize test client after database setup
        self.client = self.app.test_client()
        
        # Initialize SAM processor
        from app.processing.sam_processor import SAMProcessor
        self.app.sam_processor = SAMProcessor(self.app.config.get('SAM_MODEL_PATH', 'test_model_path'))
        
        # Create test directories
        self.test_dir = Path('test_storage')
        self.scenes_dir = self.test_dir / 'scenes'
        self.components_dir = self.test_dir / 'components'
        self.temp_dir = self.test_dir / 'temp'
        
        for dir_path in [self.scenes_dir, self.components_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.app.config['UPLOAD_FOLDER'] = str(self.temp_dir)
        
        # Verify database setup with a test record
        test_scene = RoomScene(
            name='Test Scene',
            category='living_room',
            file_path='test/path.jpg'
        )
        db.session.add(test_scene)
        db.session.commit()
        
        # Verify the record was created
        verify_scene = RoomScene.query.first()
        if not verify_scene:
            raise Exception("Database verification failed")
        
        # Clean up test record
        db.session.delete(verify_scene)
        db.session.commit()

    def tearDown(self):
        """Clean up test environment"""
        print("\nCleaning up test environment...")
        
        # Clean up database
        db.session.remove()
        db.drop_all()
        
        # Remove test database file
        if os.path.exists('test.db'):
            os.remove('test.db')
        print("✓ Database cleaned up")
        
        # Remove test directories
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        print("✓ Test directories removed")
        
        # Remove app context
        self.app_context.pop()
        print("✓ Test environment cleanup completed")

    def _create_blurry_image(self):
        """Create a low-quality test image that should fail validation"""
        img = Image.new('RGB', (1920, 1080), color='rgb(200, 200, 200)')
        img_array = np.array(img)
        img_array[300:500, 400:800] = [150, 75, 0]
        
        img = Image.fromarray(img_array)
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG', quality=60)
        img_io.seek(0)
        return img_io

    def _create_quality_image(self):
        """Create a high-quality test image that should pass validation"""
        image = np.full((1080, 1920, 3), 200, dtype=np.uint8)
        
        cv2.rectangle(image, (400, 300), (800, 500), (150, 75, 0), -1)
        cv2.circle(image, (1200, 400), 100, (0, 0, 0), -1)
        cv2.putText(image, "Living Room Scene", (100, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
        
        for i in range(0, 1920, 50):
            cv2.line(image, (i, 0), (i, 1080), (180, 180, 180), 1)
        
        img = Image.fromarray(image)
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        return img_io

    def test_complete_workflow(self):
        """Test the complete end-to-end workflow"""
        print("\nStarting E2E workflow test...")
        
        # Initialize scene handler with test database session
        scene_handler = SceneHandler(
            sam_processor=self.app.sam_processor,
            error_logger=ErrorLogger(),
            storage_base='test_storage'
        )

        # Step 1: Test blurry image upload (should fail)
        print("\n1. Testing blurry image upload...")
        data = {
            'file': (self._create_blurry_image(), 'blurry_scene.jpg'),
            'category': 'living_room'
        }
        response = self.client.post(
            url_for('admin.upload'),
            data=data,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'error')
        print("✓ Blurry image correctly rejected")

        # Step 2: Quality image upload (should succeed)
        print("\n2. Testing quality image upload...")
        data = {
            'file': (self._create_quality_image(), 'quality_scene.jpg'),
            'category': 'living_room'
        }
        response = self.client.post(
            url_for('admin.upload'),
            data=data,
            content_type='multipart/form-data'
        )
        print(f"Quality image upload response: {response.data}")
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'success')
        scene_id = response_data['scene_id']
        print(f"✓ Quality image accepted (scene_id: {scene_id})")
        
        # Step 3: Verify Scene Processing
        print("\n3. Verifying scene processing...")
        scene = db.session.get(RoomScene, scene_id)
        self.assertIsNotNone(scene, "Scene should exist in database")
        print("✓ Scene record created successfully")
        
        # Step 4: Get and verify components
        print("\n4. Checking detected components...")
        components = db.session.query(Component).filter_by(
            room_scene_id=scene_id
        ).all()
        self.assertTrue(len(components) > 0, "Should have detected components")
        print(f"✓ Found {len(components)} components")
        
        # Step 5: Component Review Process
        print("\n5. Testing component review process...")
        for index, component in enumerate(components):
            # First validate component
            print(f"\nProcessing component {component.id}...")
            response = self.client.get(
                url_for('admin.validate_component', component_id=component.id)
            )
            self.assertEqual(response.status_code, 200)
            print(f"✓ Component {component.id} validation checked")
            
            # Validate category
            response = self.client.post(
                url_for('admin.validate_component_category_endpoint', 
                       component_id=component.id)
            )
            self.assertEqual(response.status_code, 200)
            print(f"✓ Component {component.id} category validated")
            
            if index == 0:
                # Accept first component
                print(f"Accepting component {component.id}...")
                response = self.client.post(
                    url_for('admin.accept_component', component_id=component.id),
                    data={'notes': 'Good detection'}
                )
                self.assertEqual(response.status_code, 200)
                
                db.session.refresh(component)
                self.assertEqual(component.status, ComponentStatus.ACCEPTED)
                print(f"✓ Component {component.id} accepted")
            else:
                # Reject other components
                print(f"Rejecting component {component.id}...")
                response = self.client.post(
                    url_for('admin.reject_component', component_id=component.id),
                    data={'notes': 'Not accurate enough'}
                )
                self.assertEqual(response.status_code, 200)
                
                db.session.refresh(component)
                self.assertEqual(component.status, ComponentStatus.REJECTED)
                print(f"✓ Component {component.id} rejected")
        
        # Step 6: Verify Scene Statistics
        print("\n6. Verifying scene statistics...")
        response = self.client.get(
            url_for('admin.detailed_scene_statistics', scene_id=scene_id)
        )
        self.assertEqual(response.status_code, 200)
        
        stats = json.loads(response.data)
        basic_stats = stats['basic_stats']
        
        self.assertEqual(basic_stats['total_components'], len(components))
        self.assertEqual(basic_stats['accepted_components'], 1)
        self.assertEqual(basic_stats['rejected_components'], len(components) - 1)
        self.assertEqual(basic_stats['review_progress'], 100.0)
        print("✓ Statistics verified")
        
        # Step 7: Check Detection Accuracy
        print("\n7. Checking detection accuracy stats...")
        response = self.client.get(
            url_for('admin.detection_accuracy_stats', scene_id=scene_id)
        )
        self.assertEqual(response.status_code, 200)
        print("✓ Detection accuracy stats retrieved")
        
        # Step 8: Check Review Metrics
        print("\n8. Checking review metrics...")
        response = self.client.get(
            url_for('admin.review_metrics', scene_id=scene_id)
        )
        self.assertEqual(response.status_code, 200)
        print("✓ Review metrics retrieved")
        
        # Final verification
        print("\nFinal database state verification...")
        final_scene = db.session.get(RoomScene, scene_id)
        final_components = db.session.query(Component).filter_by(
            room_scene_id=scene_id
        ).all()
        
        self.assertIsNotNone(final_scene)
        self.assertEqual(len(final_components), len(components))
        self.assertEqual(
            sum(1 for c in final_components if c.status == ComponentStatus.ACCEPTED),
            1
        )
        self.assertEqual(
            sum(1 for c in final_components if c.status == ComponentStatus.REJECTED),
            len(components) - 1
        )
        print("✓ Final verification completed")
        
        print("\nE2E workflow test completed successfully!")

if __name__ == '__main__':
    unittest.main()