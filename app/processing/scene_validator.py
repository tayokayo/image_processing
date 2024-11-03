from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional, Dict
import cv2
import numpy as np
from pathlib import Path
import logging

class ValidationErrorType(Enum):
    FILE_NOT_FOUND = "File does not exist"
    INVALID_EXTENSION = "Invalid file extension"
    FILE_TOO_LARGE = "File size exceeds limit"
    INVALID_DIMENSIONS = "Invalid image dimensions"
    LOW_CONTRAST = "Image contrast too low"
    BAD_BRIGHTNESS = "Image brightness out of range"
    TOO_BLURRY = "Image too blurry"
    LOAD_ERROR = "Failed to load image"

    def __str__(self):
        return self.value
        
    def to_dict(self):
        return {
            'type': self.name,
            'message': self.value
        }

@dataclass
class ValidationResult:
    is_valid: bool
    error_type: Optional[ValidationErrorType] = None
    error_message: Optional[str] = None
    details: Optional[Dict] = None

class SceneValidator:
    """Validates scene images for processing"""
    
    # File validation constants
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Image dimension constants
    MIN_DIMENSIONS = (800, 600)  # width, height
    MAX_DIMENSIONS = (4000, 3000)
    
    # Image quality constants
    MIN_CONTRAST = 20
    MIN_BRIGHTNESS = 20
    MAX_BRIGHTNESS = 235
    MIN_SHARPNESS = 100

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize validator with optional logger"""
        self.logger = logger or logging.getLogger(__name__)

    def validate_scene(self, scene_path: str) -> ValidationResult:
        """
        Validate a scene image file comprehensively.
        
        Args:
            scene_path: Path to the scene image file
            
        Returns:
            ValidationResult containing validation status and any error details
        """
        try:
            # File validation
            file_result = self._validate_file(scene_path)
            if not file_result.is_valid:
                return file_result
            
            # Load image
            image = cv2.imread(scene_path)
            if image is None:
                return ValidationResult(
                    is_valid=False,
                    error_type=ValidationErrorType.LOAD_ERROR,
                    error_message=f"Failed to load image from {scene_path}"
                )
            
            # Dimension validation
            dim_result = self._validate_dimensions(image)
            if not dim_result.is_valid:
                return dim_result
            
            # Quality validation
            quality_result = self._validate_quality(image)
            if not quality_result.is_valid:
                return quality_result
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            self.logger.error(f"Validation error for {scene_path}: {str(e)}")
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )

    def _validate_file(self, file_path: str) -> ValidationResult:
        """Validate file existence, extension, and size"""
        path = Path(file_path)
        
        # Check existence
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.FILE_NOT_FOUND,
                error_message=f"File not found: {file_path}"
            )
        
        # Check extension
        if path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.INVALID_EXTENSION,
                error_message=f"Invalid extension: {path.suffix}. Allowed: {self.ALLOWED_EXTENSIONS}"
            )
        
        # Check size
        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.FILE_TOO_LARGE,
                error_message=f"File size ({file_size} bytes) exceeds limit ({self.MAX_FILE_SIZE} bytes)"
            )
        
        return ValidationResult(is_valid=True)

    def _validate_dimensions(self, image: np.ndarray) -> ValidationResult:
        """Validate image dimensions against allowed ranges"""
        height, width = image.shape[:2]
        
        if not (self.MIN_DIMENSIONS[0] <= width <= self.MAX_DIMENSIONS[0] and
                self.MIN_DIMENSIONS[1] <= height <= self.MAX_DIMENSIONS[1]):
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.INVALID_DIMENSIONS,
                error_message=f"Image dimensions ({width}x{height}) outside allowed range",
                details={
                    'current': {'width': width, 'height': height},
                    'allowed': {
                        'min': {'width': self.MIN_DIMENSIONS[0], 'height': self.MIN_DIMENSIONS[1]},
                        'max': {'width': self.MAX_DIMENSIONS[0], 'height': self.MAX_DIMENSIONS[1]}
                    }
                }
            )
        
        return ValidationResult(is_valid=True)

    def _validate_quality(self, image: np.ndarray) -> ValidationResult:
        """Validate image quality metrics"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Check contrast
        contrast = gray.std()
        if contrast < self.MIN_CONTRAST:
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.LOW_CONTRAST,
                error_message=f"Contrast ({contrast:.2f}) below minimum ({self.MIN_CONTRAST})",
                details={'contrast': contrast}
            )
        
        # Check brightness
        brightness = gray.mean()
        if brightness < self.MIN_BRIGHTNESS or brightness > self.MAX_BRIGHTNESS:
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.BAD_BRIGHTNESS,
                error_message=f"Brightness ({brightness:.2f}) outside allowed range",
                details={'brightness': brightness}
            )
        
        # Check sharpness
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < self.MIN_SHARPNESS:
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.TOO_BLURRY,
                error_message=f"Image too blurry (sharpness: {laplacian_var:.2f})",
                details={'sharpness': laplacian_var}
            )
        
        return ValidationResult(is_valid=True)