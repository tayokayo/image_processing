import os
import shutil
from datetime import datetime
from pathlib import Path
import numpy as np

class StorageManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.original_path = self.base_path / 'original'
        self.processed_path = self.base_path / 'processed'
        self._create_directories()

    def _create_directories(self):
        """Create storage directories if they don't exist"""
        self.original_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)

    def save_original(self, file_obj, filename):
        """Save original uploaded file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        file_path = self.original_path / safe_filename
        
        try:
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_obj, f)
            return str(file_path), None
        except Exception as e:
            return None, str(e)

    def save_processed(self, result_dict, original_filename, suffix='processed'):
        """Save processed image data"""
        try:
            # Extract masks and scores directly from dictionary
            masks = result_dict.get('masks')
            scores = result_dict.get('scores')
            
            if masks is None or scores is None:
                return None, "Missing masks or scores in result dictionary"

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{Path(original_filename).stem}_{suffix}_{timestamp}.npz"
            file_path = self.processed_path / filename
            
            # Save using numpy's savez_compressed
            np.savez_compressed(
                str(file_path),  # Convert Path to string
                masks=masks,
                scores=scores
            )
            
            return str(file_path), None
            
        except Exception as e:
            print(f"Error saving processed results: {str(e)}")  # Debug info
            return None, str(e)