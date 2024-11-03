# tests/test_initial_setup.py

import unittest
import os
from app import create_app
from app.config import Config
from app.processing.sam_processor import SAMProcessor

class TestInitialSetup(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after each test method"""
        self.app_context.pop()

    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'healthy')

    def test_sam_model_path_exists(self):
        """Test that the SAM model file exists"""
        self.assertTrue(os.path.exists(Config.SAM_MODEL_PATH))
        self.assertTrue(os.path.isfile(Config.SAM_MODEL_PATH))

    def test_sam_processor_initialization(self):
        """Test SAM processor initialization"""
        processor = SAMProcessor(Config.SAM_MODEL_PATH)
        self.assertIsNotNone(processor)
        self.assertIsNotNone(processor.device)

    def test_sam_model_loading(self):
        """Test SAM model loading"""
        processor = SAMProcessor(Config.SAM_MODEL_PATH)
        success, message = processor.load_model()
        self.assertTrue(success)
        self.assertTrue(processor.is_model_loaded())

    def test_main_route(self):
        """Test the main route that loads SAM"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.json)
        self.assertIn('message', response.json)
        self.assertIn('device', response.json)
        self.assertEqual(response.json['status'], 'success')

    def test_sam_processor_device_type(self):
        """Test that device type is correctly identified"""
        processor = SAMProcessor(Config.SAM_MODEL_PATH)
        self.assertIn(str(processor.device), ['cpu', 'cuda'])

if __name__ == '__main__':
    unittest.main()