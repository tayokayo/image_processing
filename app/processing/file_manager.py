import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import json

class FileManager:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.scenes_path = self.base_path / 'scenes'
        self.components_path = self.base_path / 'components'
        self.processed_path = self.base_path / 'processed'
        self.metadata_path = self.base_path / 'metadata'
        self._create_directories()
    
    def _create_directories(self):
        """Create all required directories"""
        for path in [self.scenes_path, self.components_path, 
                    self.processed_path, self.metadata_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def save_scene(self, file_obj, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """Save a room scene file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{filename}"
            file_path = self.scenes_path / safe_filename
            
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_obj, f)
            return str(file_path), None
        except Exception as e:
            return None, str(e)
    
    def save_component(self, file_obj, filename: str, scene_id: int) -> Tuple[Optional[str], Optional[str]]:
        """Save a component file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"scene_{scene_id}_{timestamp}_{filename}"
            file_path = self.components_path / safe_filename
            
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_obj, f)
            return str(file_path), None
        except Exception as e:
            return None, str(e)
    
    def save_metadata(self, metadata: dict, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """Save metadata as JSON"""
        try:
            file_path = self.metadata_path / f"{filename}.json"
            with open(file_path, 'w') as f:
                json.dump(metadata, f, indent=4)
            return str(file_path), None
        except Exception as e:
            return None, str(e)
    
    def delete_file(self, file_path: str) -> Optional[str]:
        """Delete a file and return error if any"""
        try:
            Path(file_path).unlink(missing_ok=True)
            return None
        except Exception as e:
            return str(e)
    
    def get_file_path(self, filename: str, file_type: str) -> Optional[Path]:
        """Get full path for a file based on type"""
        type_map = {
            'scene': self.scenes_path,
            'component': self.components_path,
            'processed': self.processed_path,
            'metadata': self.metadata_path
        }
        
        if file_type not in type_map:
            return None
            
        return type_map[file_type] / filename