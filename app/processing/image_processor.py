import numpy as np
import cv2
from segment_anything import SamPredictor
from segment_anything.utils.transforms import ResizeLongestSide

class ImageProcessor:
    def __init__(self, sam_processor):
        self.sam_processor = sam_processor
        self.predictor = self.sam_processor.predictor
        self.transform = ResizeLongestSide(1024)  # Standard SAM input size

    def process_image(self, image_path):
        """Process an image using SAM"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return {
                    'status': 'error',
                    'masks': None,
                    'message': f'Failed to read image from {image_path}'
                }
            
            print(f"Image shape: {image.shape}")  # Debug info
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Set image in predictor
            try:
                print("Setting image in predictor...")
                self.predictor.set_image(image)
                print("Image set successfully")
            except Exception as e:
                return {
                    'status': 'error',
                    'masks': None,
                    'message': f'Error setting image in predictor: {str(e)}'
                }
            
            # Generate automatic masks using points
            try:
                print("Generating masks...")
                # Get image dimensions
                h, w = image.shape[:2]
                
                # Create a center point
                center_point = np.array([[w//2, h//2]])
                
                # Generate mask from center point with label 1 (foreground)
                masks, scores, logits = self.predictor.predict(
                    point_coords=center_point,
                    point_labels=np.array([1]),
                    multimask_output=True
                )
                print(f"Masks generated: {masks.shape if masks is not None else 'None'}")
                
                return {
                    'status': 'success',
                    'masks': masks,
                    'scores': scores,
                    'message': 'Image processed successfully'
                }
            except Exception as e:
                return {
                    'status': 'error',
                    'masks': None,
                    'message': f'Error generating masks: {str(e)}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'masks': None,
                'message': f'Processing failed: {str(e)}'
            }