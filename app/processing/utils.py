import os
from PIL import Image
from pathlib import Path

class ImageValidator:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    MAX_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ImageValidator.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_image(image_path):
        try:
            if not os.path.exists(image_path):
                return False, "File does not exist"
            
            if os.path.getsize(image_path) > ImageValidator.MAX_SIZE:
                return False, "File size exceeds 10MB limit"
            
            with Image.open(image_path) as img:
                img.verify()  # Verify it's a valid image
            return True, "Image is valid"
        except Exception as e:
            return False, str(e)