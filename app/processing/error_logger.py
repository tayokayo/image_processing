import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

class ErrorLogger:
    def __init__(self, log_dir='logs'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger('scene_processing')
        self.logger.setLevel(logging.ERROR)
        
        # Create file handler
        log_file = self.log_dir / f"processing_errors_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.ERROR)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
    
    def log_error(self, error_message: str, error_type: str, 
                 file_name: Optional[str] = None) -> None:
        """Log an error with context"""
        context = f"File: {file_name} - " if file_name else ""
        self.logger.error(
            f"{context}Type: {error_type} - Message: {error_message}"
        )

    def log_processing_status(self, scene_id: int, status: str, 
                            details: Optional[str] = None) -> None:
        """Log processing status"""
        message = f"Scene {scene_id} - Status: {status}"
        if details:
            message += f" - Details: {details}"
        if status == 'error':
            self.logger.error(message)
        else:
            self.logger.info(message)