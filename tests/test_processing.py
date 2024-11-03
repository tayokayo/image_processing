import unittest
import os
import shutil
from pathlib import Path
import numpy as np
from PIL import Image

from app.processing.utils import ImageValidator
from app.processing.storage import StorageManager
from app.processing.image_processor import ImageProcessor
from app.processing.error_logger import ErrorLogger
from app.processing.sam_processor import SAMProcessor

class TestImageProcessing(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path('test_storage')
        self.test_dir.mkdir(exist_ok=True)
        
        # Create test image
        self.test_image_path = self.test_dir / 'test.jpg'
        self._create_test_image()
        
        # Initialize components
        self.storage_manager = StorageManager(self.test_dir)
        self.error_logger = ErrorLogger(self.test_dir / 'logs')
        
        # Initialize SAM and image processor
        self.sam_processor = SAMProcessor(os.getenv('SAM_MODEL_PATH'))
        self.sam_processor.load_model()
        self.image_processor = ImageProcessor(self.sam_processor)

    def tearDown(self):
        """Clean up test fixtures"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _create_test_image(self):
        """Create a simple test image"""
        img = Image.new('RGB', (100, 100), color='red')
        img.save(self.test_image_path)

    def test_image_validator(self):
        """Test image validation"""
        # Test valid image
        is_valid, message = ImageValidator.validate_image(self.test_image_path)
        self.assertTrue(is_valid)
        
        # Test invalid file
        is_valid = ImageValidator.allowed_file('test.txt')
        self.assertFalse(is_valid)

    def test_storage_manager(self):
        """Test storage management"""
        # Test directory creation
        self.assertTrue(self.storage_manager.original_path.exists())
        self.assertTrue(self.storage_manager.processed_path.exists())
        
        # Test file saving
        with open(self.test_image_path, 'rb') as f:
            path, error = self.storage_manager.save_original(f, 'test.jpg')
        self.assertIsNotNone(path)
        self.assertIsNone(error)
        self.assertTrue(os.path.exists(path))

    def test_image_processor(self):
        """Test image processing"""
        result = self.image_processor.process_image(str(self.test_image_path))
        print(f"Processing result: {result}")  # Debug info
        self.assertEqual(result['status'], 'success')
        self.assertIsNotNone(result['masks'])
        # Verify masks is a numpy array
        self.assertTrue(isinstance(result['masks'], np.ndarray))
        # Verify we got scores
        self.assertIn('scores', result)

    def test_error_logger(self):
        """Test error logging"""
        self.error_logger.log_error(
            error_message="Test error",
            error_type="TestError",
            file_name="test.jpg"
        )
        log_files = list(Path(self.error_logger.log_dir).glob('*.log'))
        self.assertTrue(len(log_files) > 0)

    def test_end_to_end_processing(self):
        """Test complete processing pipeline"""
        # 1. Validate image
        is_valid, message = ImageValidator.validate_image(self.test_image_path)
        self.assertTrue(is_valid)
        
        # 2. Save original
        with open(self.test_image_path, 'rb') as f:
            path, error = self.storage_manager.save_original(f, 'test.jpg')
        self.assertIsNotNone(path)
        
        # 3. Process image
        result = self.image_processor.process_image(path)
        self.assertEqual(result['status'], 'success')
        
        # 4. Save results
        save_path, error = self.storage_manager.save_processed(
            result_dict=result,
            original_filename='test.jpg'
        )
        
        # Debug output
        if error:
            print(f"Save error: {error}")
        else:
            print(f"Successfully saved to: {save_path}")
        
        self.assertIsNotNone(save_path, f"Save path is None. Error: {error}")
        self.assertIsNone(error, f"Got error while saving: {error}")
        
        # 5. Verify saved file exists and can be loaded
        if save_path:  # Only try to verify if save_path exists
            self.assertTrue(os.path.exists(save_path))
            try:
                loaded_data = np.load(save_path)
                self.assertIn('masks', loaded_data)
                self.assertIn('scores', loaded_data)
                print(f"Successfully loaded saved data. Available arrays: {loaded_data.files}")
            except Exception as e:
                print(f"Error verifying saved data: {str(e)}")

if __name__ == '__main__':
    unittest.main()